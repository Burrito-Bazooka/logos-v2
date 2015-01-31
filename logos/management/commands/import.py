#! /usr/bin/env python

#import psutil # Used to determine available RAM
import sys
import gc
import os
import re
import csv
import pdb
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from optparse import OptionParser, make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import commit_on_success
from django.db import connection, reset_queries

from django.db.models import Max

from logos.settings import BIBLES_DIR, DATABASES

from logos.models import BibleTranslations, BibleBooks, BibleVerses, \
    BibleConcordance, BibleDict

from _booktbl import book_table
from logos.constants import PUNCTUATION, STOP_WORDS

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import the translations'

    extra_options = (

        make_option('--replace-version',action='store',
                    help="Only replace the specified translation in the" + \
                    "database.  Should be a folder name in bibles/"),

    )
    option_list = BaseCommand.option_list + extra_options


    def handle(self, *args, **options):
        logger.debug ("args = "+str(args))
        logger.debug ("options = "+ str(options))

#        if DATABASES['bibles']['ENGINE'].endswith('sqlite3'):
#            vm = psutil.virtual_memory()
#            cursor = connection.cursor()
#            cursor.execute("PRAGMA Journal_mode = MEMORY")
#            cursor.execute("PRAGMA Page_size")
#            row = cursor.fetchone()
#            page_size = row[0]
#            # use 75% of available VM for cache
#            cache_size = int(.75 * vm.available / page_size)
#            cursor.execute("PRAGMA Cache_Size = "+str(cache_size))
#            print "page_size = " + str(page_size) + " bytes"
#            print "cache_size = " + str(cache_size) + " pages"

        
        if options['replace_version']:
            version = options['replace_version']
            biblepath = BIBLES_DIR + os.sep + version        
            if not os.path.exists(biblepath):
                print "Version %s does not exists in bibles/" % (version,)
                return
        else:
            # don't bother repopulating the strongs tables if we are just
            # replacing a single translation
            try:
                import_strongs_tables() 
            except IOError:
                # If dict folder doesn't exist then just carry on
                pass
        import_trans(options)
        import_concordance(options)
       
def import_strongs_tables():

    cache = []
    idx = 0

    #BibleDict.objects.all().delete()
    for lang,prefix in (('grk', 'G'), ('heb', 'H')):
        print lang, prefix
        file1 = os.path.join(BIBLES_DIR, 'dict', lang)
        f = open(file1, 'rb')
        for line in f.readlines():
            
            mch = re.match('(\d+)\s+(.*)', line)
            if mch:
                num = prefix+str(mch.group(1))
                text = mch.group(2).decode("utf8", "replace")
                try:
                    dict_obj = BibleDict.objects.get(strongs=num)
                except BibleDict.DoesNotExist:
                    dict_obj = BibleDict(id=idx+1, strongs=num, description=text)
                    if len(cache) > 0 and dict_obj.strongs == cache[-1].strongs:
                        pdb.set_trace()
                    cache.append(dict_obj)
                idx += 1
            else:
                print "strange dict line : " + line

            # This horrible kludge is because the bulk_create
            # method fails somewhere in the middle when inserting
            # large numbers of records (but does not fail when inserting
            # them individually) so I temporarily reduce the number of 
            # objects to insert and then increase it again.  Does this only happen
            # when using Sqlite3 as a database? Is this a known bug in Django?
            if idx > 6000:
                modulus = 100
            elif idx > 5620:
                modulus = 1
            elif idx > 5600:
                modulus = 10
            else:
                modulus = 200
                
            ### End Kludge ###
            
            if  idx % modulus == 0:
                if len(cache) ==0:
                    print "#",
                else:
                    print "(%d, %s) " % (idx,cache[-1].strongs),
                    BibleDict.objects.bulk_create(cache)
                    cache = []
                    gc.collect()
              
            
        f.close()
        BibleDict.objects.bulk_create(cache)

def import_trans(options):
    print "importing translations..."
    print BIBLES_DIR
    valid_books = map(lambda x:x[0], book_table)

    def process_books(version):
        biblepath = BIBLES_DIR + os.sep + version
        trans_file = biblepath + os.sep + "trans_file.csv"
        print biblepath
        for bk in valid_books:
            book_path = biblepath + os.sep + bk
            if os.path.exists(book_path):
                pass
            elif os.path.exists(book_path + ".txt"):
                book_path = book_path + ".txt"
            else:
                print "Could not find book : " + book_path
                continue
            translation = version
            add_book_to_db(translation, book_path)


        # process apocraphyl books in folder (if any).
        # Uses the csv file in the same folder to determine what are
        # the apocraphyl files.
        if os.path.exists(trans_file):
            with open(trans_file, 'rb') as csvfile:
                csvreader = csv.reader(csvfile)
                for row in csvreader:
                    long_name = row[0]
                    short_name = row[1]
                    book_path = biblepath + os.sep + short_name + ".txt"
                    if os.path.exists(book_path):
                        add_book_to_db(translation, book_path, long_name=long_name)
                    else:
                        print "Error in adding apocraphyl book %s %s" %(version, short_name)
          
    if options['replace_version']:
        version = options['replace_version']
        print "Purging translation " + version
        purge_translation(version)
        process_books(version)
    else:
        for this_dir in os.listdir(BIBLES_DIR):
            if this_dir[0] != '_' and this_dir != 'dict':
                biblepath = BIBLES_DIR + os.sep + this_dir
                print biblepath
                process_books(this_dir)

            
def import_concordance(options):
    print "Importing concordance ..."
    if options['replace_version']:
        version = options['replace_version']
        purge_concordance(version)
    populate_concordance(options)

def purge_concordance(version):
    print "Purging concordance of " + version
    try:
        trans = BibleTranslations.objects.get(name=version)
    except ObjectDoesNotExist:
        return
    BibleConcordance.objects.filter(trans=trans)      

def populate_concordance(options):
    """ Run through the bible verse database looking up all verses
    and create concordance records for each word (except common words)"""


    def really_pop_concordance(version):
        conc_cache = []
        try:
            trans = BibleTranslations.objects.get(name=version)
        except ObjectDoesNotExist:
            return
        if BibleConcordance.objects.exists():
            next_id = BibleConcordance.objects.all().\
                aggregate(Max('id'))['id__max']+1
            last_rec = BibleConcordance.objects.filter(trans=trans).last()
            if last_rec:

                lbook = last_rec.book
                lchapter = last_rec.chapter
                lverse = last_rec.verse
                print "continuing from %s %d:%d" % (lbook.long_book_name, lchapter, lverse)
                bv_id = BibleVerses.objects.filter(trans=trans, \
                                book = lbook, chapter = lchapter, \
                                verse=lverse).first().id
                bv = BibleVerses.objects.filter(trans = trans, pk__gt = bv_id).iterator()  # iterator uses less memory
            else:
                print "No records for this translation yet"
                bv = BibleVerses.objects.filter(trans = trans).iterator()



        else:
            next_id = 1
            bv = BibleVerses.objects.filter(trans=trans).iterator()  # iterator uses less memory

        idx = 0
        iidx = 0
        for vs in bv:

            text = vs.verse_text
            words = re.split('\s+', text.lower())
            for word_id, wd in enumerate(words):
                wd = re.sub(PUNCTUATION, "", wd)
                if wd == '': continue


                wd_lower = wd.lower()
                assert wd_lower != ''
                if wd_lower not in STOP_WORDS:

                    if BibleConcordance.objects.\
                    filter(trans = vs.trans,
                           book = vs.book,
                           chapter = vs.chapter,
                           verse = vs.verse,
                           word_id = word_id).exists():
                           pass

                    else:
                        conc = BibleConcordance(id = next_id,
                                                trans = vs.trans,
                                                book = vs.book,
                                                chapter = vs.chapter,
                                                verse = vs.verse,
                                                word_id = word_id,
                                                word = wd_lower)
                        next_id += 1
                        conc_cache.append(conc)

                    idx+= 1
                    if  idx % 500 == 0:
                        if len(conc_cache) ==0:
                            print "#",
                        else:
                            print ".",
                            BibleConcordance.objects.bulk_create(conc_cache)
                            conc_cache = []
                        iidx += 1
                        if iidx % 35 == 0: print
                        gc.collect()

                        # reset_queries, workaround for large databases
                        # See http://travelingfrontiers.wordpress.com/2010/06/26/django-memory-error-how-to-work-with-large-databases/
                        # and https://docs.djangoproject.com/en/dev/faq/models/#why-is-django-leaking-memory
                        reset_queries()

        BibleConcordance.objects.bulk_create(conc_cache)
        conc_cache = []

        
    
    if options['replace_version']:
        version = options['replace_version']
        print "populate concordance with " + version
        really_pop_concordance(version)
    else:    
        for trans in BibleTranslations.objects.all().iterator():
        
            trans_name = trans.name
            print "Adding missing translation to concordance", trans.name

            really_pop_concordance(trans.name)



@commit_on_success
def purge_translation(translation):
    """ Delete entire translation/version from database """
    try:
        trans = BibleTranslations.objects.get(name=translation)
    except ObjectDoesNotExist:
        return
    BibleVerses.objects.filter(trans = trans).delete()
    BibleBooks.objects.filter(trans = trans).delete()
    trans.delete()


@commit_on_success
def add_book_to_db(translation, book_path, long_name = None):
    book = os.path.splitext(book_path)[0]
    book = os.path.split(book)[1]

    try:
        new_trans = BibleTranslations.objects.get(name=translation)
    except ObjectDoesNotExist:

        new_trans = BibleTranslations(name = translation)
        new_trans.save()
        print "saved new trans " + translation
        trans = new_trans.pk

    if long_name:
        max_bb = BibleBooks.objects.filter(trans = new_trans).aggregate(Max('book_idx'))
        idx = max_bb['book_idx__max']+1
        long_book = long_name
    else:
        long_book, idx = get_long_book_name(book)
    mch = re.match("^([^\.]+)", book)
    if mch:
        base_book = mch.group(1)
    assert base_book

    if not BibleBooks.objects.\
        filter(trans = new_trans, canonical = base_book).exists():
        print "adding book ", long_book
        bib_book = BibleBooks(trans = new_trans,
                              long_book_name= long_book,
                              book_idx = int(idx),
                              canonical = base_book)
        bib_book.save()

        populate_verses(new_trans, bib_book, book_path)
    else:
        print "%s : %s book already exists - skipping" % (translation, base_book,)

    gc.collect()

def populate_verses(trans, book_id, filename):
    """ Add a book (of the bible) file in CancelBot 
    format to the database """
    book_cache = []
    if BibleVerses.objects.exists():
        next_id = BibleVerses.objects.all().\
            aggregate(Max('id'))['id__max']+1
    else:
        next_id = 1

    f = open(filename, "r")
    for lineno, ln in enumerate(f.readlines()):
        if ln.strip() != '':
            mch = re.match('[^\d]*(\d+):(\d+)(\s+|:)(.*)', ln)
            if mch:
                ch = int(mch.group(1))
                vs = int(mch.group(2))
                # bug?  causes double quotes in output
                #txt = re.sub('\'', '\'\'', mch.group(4))

                #txt = re.sub(r'\\', r'\\\\', txt)
                
                txt = re.sub('[^\x20-\x7F]', '', mch.group(4))
                bv = BibleVerses(id = next_id,
                                 trans = trans,
                                 book = book_id,
                                 chapter = ch,
                                 verse = vs,
                                 verse_text = txt)
                next_id += 1
                book_cache.append(bv)


            else:
                print "weird -> ", filename, lineno, ln


    BibleVerses.objects.bulk_create(book_cache)

def populate_strongs_tables():

    BibleDict.objects.all().delete()
    file1 = os.path.join(BIBLES_DIR, 'dict', 'grk')
    f = open(file1, 'rb')
    for line in f.readlines():

        mch = re.match('(\d+)\s+(.*)', line)
        if mch:
            num = "G"+str(mch.group(1))
            text = mch.group(2) #.encode("utf8", "replace")
            # fix unicode errors
            text = re.sub('[\x80-\xFF]', '', str(text))
            dict = BibleDict(strongs = num, description = text)
            dict.save()
    f.close()

    file1 = os.path.join(BIBLES_DIR, 'dict', 'heb')
    f = open(file1, 'rb')
    for line in f.readlines():
        mch = re.match('(\d+)\s+(.*)', line)
        if mch:
            num = "H"+str(mch.group(1))
            text = str(mch.group(2)) #.decode("utf8", "replace")
            # fix unicode errors
            text = re.sub('[\x80-\xFF]', '', str(text))
            dict = BibleDict(strongs = num, description = text)
            dict.save()


    f.close()


def get_long_book_name(book):
    idx = 0
    for bk, long_bk in book_table:
        if book == bk:
            return (long_bk, idx)
        idx += 1
    return None
