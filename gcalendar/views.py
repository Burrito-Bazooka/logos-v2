from __future__ import absolute_import
from django.shortcuts import render, redirect
from django.forms.models import model_to_dict
from django.contrib import messages
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required

from oauth2client.client import OAuth2WebServerFlow
from oauth2client.django_orm import Storage

import httplib2
from apiclient import discovery
import datetime
import dateutil
import dateutil.parser
import pytz

from .forms import SiteSetupForm, EventForm
from .models import SiteModel, FlowModel, CredentialsModel

# Create your views here.
@login_required()
def site_setup(request):
    if request.method == "POST":
        form = SiteSetupForm(request.POST)
        if form.is_valid():
            SiteModel.objects.all().delete()
            client_id = form.cleaned_data['client_id']
            client_secret = form.cleaned_data['client_secret']
            mdl = SiteModel(client_id = client_id,
                    client_secret = client_secret)
            mdl.save()
    else:
        mdl = SiteModel.objects.first()
        if mdl:
            model_data = model_to_dict(mdl, fields = ['client_id', 'client_secret'])
            form = SiteSetupForm(initial=model_data)
        else:
            form = SiteSetupForm()
    return render(request, 'gcal/site_setup.html', {'form':form})


@login_required()
def user_setup(request):
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    credentials = storage.get()
    mdl = SiteModel.objects.first()
    domain = Site.objects.get_current().domain
    flow = OAuth2WebServerFlow(client_id=mdl.client_id,
                               client_secret=mdl.client_secret,
                               scope='https://www.googleapis.com/auth/calendar',
                               redirect_uri="http://"+domain + '/gcal/callback')
    f, created = FlowModel.objects.get_or_create(id = request.user)
    f.flow = flow
    f.save()
    url = flow.step1_get_authorize_url()+"&approval_prompt=force" 
    if credentials:
        return render(request, 'gcal/user_setup.html', {'credentials':credentials, 'url':url})
    else:

        return render(request, 'gcal/user_setup.html', {'url':url})


def oauth_callback(request):
    code = request.GET['code']
    flow = FlowModel.objects.get(id = request.user).flow
    credentials = flow.step2_exchange(code)
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    storage.put(credentials)
    messages.add_message(request, messages.INFO, 'Google Authentication Successful')
    return redirect('user_setup')

@login_required()
def list(request):

    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    credentials = storage.get()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    eventsResult = service.events().list(
        calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    for event in events:
        if 'date' in event['start']:
            event['start_date'] = dateutil.parser.parse(event['start']['date'])
        elif 'dateTime' in event['start']:
            event['start_datetime'] = dateutil.parser.parse(event['start']['dateTime'])
        else:
            event.start_date = None  # unhandled error
#        dt = dateutil.parser.parse(start_date)
#        estr = "{} {}".format(str(dt), event['summary'])
#        self.notice(nick, estr)
#
    return render(request, 'gcal/list.html', {'events':events})

@login_required()
def new_event(request):
    tz = pytz.timezone('Pacific/Auckland')
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            
            storage = Storage(CredentialsModel, 'id', request.user, 'credential')
            credentials = storage.get()
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('calendar', 'v3', http=http)
            
            start_time = form.cleaned_data['start_time']
            start_date = form.cleaned_data['start_date']

            event = {
              'summary': form.cleaned_data['summary'],
              'location': form.cleaned_data['location'],
              'description': form.cleaned_data['description'],
            }

            if start_time:
                d = datetime.datetime.combine(start_date, start_time)
                start = (tz.localize(d)).isoformat()
                event['start'] = {'dateTime':start, 'timeZone': 'Pacific/Auckland'}
                duration = int(form.cleaned_data['duration'])
                td = datetime.timedelta(minutes = duration)
                end_date = tz.localize(d + td).isoformat()
                event['end'] = {'dateTime':end_date, 'timeZone': 'Pacific/Auckland'}
            else:
                d = start_date
                start = start_date.isoformat()
                event['start'] = {'date':start, 'timeZone': 'Pacific/Auckland'}
                event['end'] = event['start']
            
            event = service.events().insert(calendarId='primary', body=event).execute()
            messages.add_message(request, messages.INFO, 'Calendar Event Created Successful')
            return redirect('list')
    else: # GET
        start_date = datetime.datetime.now(tz).date().strftime('%d/%m/%y')
        form = EventForm(initial={'start_date':start_date})
    return render(request, 'gcal/new_event.html', {'form':form})


@login_required()
def event_detail(request, event_id):
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    credentials = storage.get()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    event = service.events().get(calendarId='primary', eventId=event_id).execute()

    if 'date' in event['start']:
        event['start_date'] = dateutil.parser.parse(event['start']['date'])
        start_datetime = None
    elif 'dateTime' in event['start']:
        start_datetime = dateutil.parser.parse(event['start']['dateTime'])
        event['start_date'] = start_datetime.date()
        event['start_time'] = start_datetime.time()


    if start_datetime and 'dateTime' in event['end']:
        end_date = dateutil.parser.parse(event['end']['dateTime'])
        event['duration'] = (end_date - start_datetime).seconds/60

    ctx = {'event':event}
    if request.method == 'POST':
        ctx.update({'confirm':True})
        if 'confirm' in request.POST and \
        request.POST['confirm'] == 'Yes':
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            messages.add_message(request, messages.INFO, 'Event Deleted Successfully')
            return redirect('list')
    return render(request, 'gcal/detail.html', ctx)


