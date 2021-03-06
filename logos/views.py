# logos.views
from __future__ import absolute_import

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.core import serializers

from .forms import SettingsForm, UserSettingsForm
from .models import Settings, BotsRunning, Plugins, NetworkPlugins, RoomPlugins, NetworkPermissions, RoomPermissions
from logos.roomlib import get_user_option, set_user_option

import copy
import pickle
import socket
import logging
import inspect

import xmlrpclib
from bot.pluginDespatch import Plugin

from django.conf import settings 
logger = logging.getLogger(__name__)
logging.config.dictConfig(settings.LOGGING)

# def room_settings(request):
    # context = {}
    # return render(request, 'logos/room_settings.html', context)
    
def root_url(request):
    if request.user.is_authenticated():
        return redirect('/accounts/profile')
    else:
        return redirect('/accounts/login/?next=%s' % request.path)

def _get_settings():
    settings = Settings.objects.all()
    d = {}
    for s in settings:
        d[s.option] = s.value
    return d
        
def _get_rpc_url():
    settings = _get_settings()
    host = settings.get('rpc_host', None)
    port = settings.get('rpc_port', None)
    url = 'http://%s:%s/' % (host,port)
    return url

    
@login_required()
def user_settings(request):
    if request.method == "GET":
        trigger = get_user_option(request.user, "trigger")
        if trigger:
            form = UserSettingsForm(initial={'trigger_choice':trigger})
        else:
            form = UserSettingsForm()
    else: # POST
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            trigger = form.cleaned_data['trigger_choice']
            set_user_option(request.user, 'trigger', trigger)
            messages.add_message(request, messages.INFO, 'User Trigger Successfully set to "'+trigger+'"')
            return redirect('plugins')

    return render(request, 'logos/user_settings.html', {'form':form})

@login_required()
def admin(request):
    return HttpResponseRedirect(reverse('logos.views.bots'))

@login_required()
def bots(request):
    bots_running = BotsRunning.objects.all()
    bots = []
    for bot in bots_running:
        url = "http://localhost:{}/".format(bot.rpc)
        srv = xmlrpclib.Server(url)
        dead = False
        try:
            networks = srv.get_networks()
        except Exception as e:
            print e.errno
            # error 111 is connection refused
            if e.errno == 10061 or e.errno == 111:
                dead = True
            else:
                raise
            networks = []
        print networks
        bots.append({'id': bot.id, 'pid':bot.pid, 'alive':not dead, 'rpc':bot.rpc, 'networks':networks})
    context = {'bots':bots}
    return render(request, 'logos/bots.html', context)

def configure_plugins(app, plugins):
    """Populate plugins with configuration view information"""
    for plugin in plugins:
        # 'logos' app causes confusion because it
        # it matches the Plugin class

        try:
            plugin_mod = __import__(app + ".bot_plugin").bot_plugin
            for attr in dir(plugin_mod):
                a1 = getattr(plugin_mod, attr)
                # Check if the class is a class derived from 
                # bot.PluginDespatch.Plugin
                # but is not the base class only

                if inspect.isclass(a1) and \
                a1 != Plugin and \
                issubclass(a1, Plugin) and \
                hasattr(a1, 'plugin') and \
                a1.plugin[0] == plugin.plugin.name:  
                    if app == 'logos': 
                        plugin.user_view = 'logos.views.user_settings'
                        return

                    appmod = __import__(app + ".settings").settings
                    if hasattr(appmod, 'USER_SETTINGS_VIEW'):
                        plugin.user_view = appmod.USER_SETTINGS_VIEW
                        logger.debug( "Add user settings for " + app) 
                    if hasattr(appmod, 'SUPERUSER_SETTINGS_VIEW'):
                        plugin.superuser_view = appmod.SUPERUSER_SETTINGS_VIEW
                        logger.debug( "Add superuser settings for " + app) 
                    if hasattr(appmod, 'DASHBOARD_VIEW'):
                        plugin.dashboard_view = appmod.DASHBOARD_VIEW
                        logger.debug( "Add dashboard settings for " + app) 
                    return


        except ImportError:
            pass



@login_required()    
def plugins(request):
    plugins = NetworkPlugins.objects.order_by('plugin__name')
    networks = []
    for app in settings.INSTALLED_APPS:
        configure_plugins(app, plugins)

    for plugin in plugins:
        if plugin.network not in networks:
            networks.append(plugin.network)
    context = {'plugins':plugins, 'networks':networks, 'networkpermissions':NetworkPermissions}
    return render(request, 'logos/plugins.html', context)

@login_required()    
def networkplugins(request, net_plugin_id):
    plugin = get_object_or_404(NetworkPlugins, pk=net_plugin_id)
    if request.method == 'POST':
        if 'activate' in request.POST:
            if 'Activate' in request.POST['activate']:
                plugin.enabled = True
                plugin.save()
            if 'Deactivate' in request.POST['activate']:
                plugin.enabled = False
                plugin.save()
    context = {'plugin':plugin, 'networkpermissions':NetworkPermissions,
                'roompermissions':RoomPermissions}
    return render(request, 'logos/network_plugins.html', context)
    

@login_required()    
def plugin_room_activate(request, plugin_id):
    plugin = get_object_or_404(RoomPlugins, pk=plugin_id)
    if plugin.enabled:
        plugin.enabled = False
    else:
        plugin.enabled = True
    plugin.save()
    return HttpResponseRedirect(reverse('logos.views.networkplugins', args=(plugin.net.id,)))


    
@login_required()    
def deletenetworkplugins(request, network):
    if request.method == 'POST':
        if request.POST['confirm'] == 'Yes':
            NetworkPlugins.objects.filter(network = network).delete()
        return HttpResponseRedirect(reverse('logos.views.plugins'))
            
    message = 'Are you sure you wish to delete all plugin entries for "{}"'.format(network)
    context = {'network':network, 'heading':'Network Delete Confirmation',
        'detail':message}
    return render(request, 'logos/confirm.html', context)
    
@login_required()
def bot_view(request, id):
    bot = BotsRunning.objects.get(pk=id)
    url = "http://localhost:{}/".format(bot.rpc)
    srv = xmlrpclib.Server(url)
    factories = srv.get_factories()
    context = {'factories':factories, 'bot':bot}
    return render(request, 'logos/factories.html', context)
    
    
    
@login_required()
def profile(request):
    context = {}
    return render(request, 'logos/profile.html', context) 
    
#    if request.method == 'GET':
#        settings = _get_settings()
#        host = settings.get('rpc_host', None)
#        port = settings.get('rpc_port', None)
#        form = SettingsForm(initial=settings)
#    elif request.method == 'POST':
#        form = SettingsForm(request.POST)
#        s = Settings()
#        if form.is_valid():
#            for fld in form:
#                try:
#                    obj = Settings.objects.get(option = fld.name)
#                    obj.option = fld.name
#                    obj.value = fld.value()
#                    obj.save()
#                except Settings.DoesNotExist:
#                    obj = Settings(option=fld.name, value=fld.value())
#                    obj.save()

#        settings = _get_settings()
#        host = settings.get('rpc_host', None)
#        port = settings.get('rpc_port', None)
        
#    if not host or not port:
#        context = {'form':form, 'errors': 'Missing connection parameters'}
#        return render(request, 'logos/profile.html', context)        
#    try:
#        url = _get_rpc_url()
#        srv = xmlrpclib.Server(url)
#        network = srv.get_network_name()
        
#        # Can't send/receive objects across twisted RPC, must pickle
#        nicks_pickle = srv.get_nicks_db()
#        nicks_db = pickle.loads(nicks_pickle)
        
#        rooms = nicks_db.get_rooms()
#        room_info = nicks_db.nicks_in_room
#        nicks_info = nicks_db.nicks_info
        
#        # fix a problem with the fact that templates don't
#        # like hyphenated variables in templates
#        for k in nicks_info.keys():
#            if 'bot-status' in nicks_info[k]:
#                nicks_info[k]['bot_status'] = nicks_info[k]['bot-status']
#            else:
#                nicks_info[k]['bot_status'] = False

#        context = {'network': network, 'rooms': rooms, 'rooms_info': room_info,
#                   'nicks_info': nicks_info, 'form':form}
        
#        return render(request, 'logos/profile.html', context)
#    except socket.error:
#        context = {'form':form, 'errors': 'Could not connect to Logos bot'}
#        return render(request, 'logos/profile.html', context)

@login_required()    
def bot_approval(request, req_id):
    br = BotRequests.objects.get(pk=req_id)
    

@login_required()
def bot_deny(request, req_id):
    pass


@login_required()
def bot_colours(request):
    url = _get_rpc_url()
    srv = xmlrpclib.Server(url)
    network = srv.get_network_name()
    nicks_pickle = srv.get_nicks_db()
    nicks_db = pickle.loads(nicks_pickle)
    rooms = nicks_db.get_rooms()     

    if request.method == "POST":
        room = "#" + request.POST["room"]
        network = request.POST["network"]
        data = []
        for k in request.POST.keys():
            if k not in ("room", "network", "csrfmiddlewaretoken"):
                v = request.POST[k]
                try:
                    obj = BibleColours.objects.get\
                        (network=network, room=room,
                         element=k)
                except BibleColours.DoesNotExist:
                    obj = BibleColours(network=network, room=room,
                         element=k, mirc_colour=v)
                else:
                    obj.mirc_colour = v
                obj.save()
        messages.add_message(request, messages.INFO,
                             'Colour settings for %s saved' % room)
        return HttpResponseRedirect(reverse('logos.views.bot_colours'))

    else:
       
           
        context = {'network':network, 'rooms':rooms}
        return render(request, 'logos/logos_colours.html', context)

@login_required()
def ajax_get_room_colours(request, network, room):
    try:
        room_colours = BibleColours.objects.filter\
            (network=network, room='#'+room)
    except BibleColours.DoesNotExist:
        return HttpResponse(None)

    data = serializers.serialize("json", room_colours)

    return HttpResponse(data)

@login_required()
def nicks_css(request):
    context = {}
    return render(request, 'logos/nicks_css.html', context)
    
