# README #

This README would normally document whatever steps are necessary to get your application up and running.

### What is this repository for? ###

* Quick summary

Project is loosely based on the [CancelBot Project](http://cancelbot.sourceforge.net/home.html)
Has been in private development since at least mid 2014 and only in Dec 2014 
released publicly on GitHub.  Is compatible with CancelBot bible translations.

Features include:
  * Simple bible verse lookups
  * Fast concordance searches
  * Strongs number lookups
  * Optional Django webserver for setup (in progress)
  * Plugin architecture for extending bot
  * Written in Python using Twisted and Django frameworks


* Version

Version 0.90

* [Learn Markdown](https://bitbucket.org/tutorials/markdowndemo)

### Summary of set up for Linux ###

#### Centos ####
```bash
# yum groupinstall "Development Tools"
# yum install python-devel
# yum install python-pip
```

As normal user ...

```bash
$ git clone https://github.com/kiwiheretic/logos-v2.git ~/logos2
$ cd ~/logos2
$ virtualenv ~\venvs\logos2
$ source ~\venvs\logos2\bin\activate

$ pip install -r requirements.txt
$ python manage.py syncdb
$ python manage.py syncdb --database=bibles
$ python manage.py syncdb --database=settings
$ python manage.py import
```

#### Ubuntu ####
```bash
$ sudo apt-get install python-dev python-pip build-essentials
$ sudo pip install virtualenv
$ virtualenv ~\venvs\logos2
$ source ~\venvs\logos2\bin\activate

$ git clone https://github.com/kiwiheretic/logos-v2.git ~/logos2
$ cd ~/logos2
$ pip install -r requirements.txt
$ python manage.py syncdb
$ python manage.py syncdb --database=bibles
$ python manage.py syncdb --database=settings
$ python manage.py import
```

### Summary of set up for Microsoft Windows ###

* Download Python 2.7 from [https://www.python.org/downloads/windows/](Python 2.7 for Windows)  
* [Install get-pip.py](https://bootstrap.pypa.io/get-pip.py) to computer and run it from python. 
* Change into project directory
```
python get-pip.py
pip install virtualenv
mkdir \venvs
virtualenv \venvs\logos2
\venvs\logos2\Scripts\activate

pip install -r requirements.txt
manage.py syncdb
manage.py syncdb --database=bibles
manage.py syncdb --database=settings
manage.py import
```

The last import command may need to be run several times if a 
MemoryError results.  Import automatically continues where left off.
Haven't yet tracked down what causes this.

* Configuration

To be written

* Dependencies

  * Twisted 14.0
  * Django 1.7
  * Python 2.7
  * django-registration-redux 1.1
  * psutil 2.1.3
  * zope.interface 4.1.1
  
* Database configuration

Very little.  Uses sqlite3.

* How to run tests

Still to come

* Deployment instructions

### Contribution guidelines ###

* Writing tests

Open to suggestions

* Code review
* Other guidelines

### Who do I talk to? ###

* Repo owner or admin

kiwiheretic (at) myself (dot) com

* Other community or team contact