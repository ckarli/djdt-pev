import json
import threading

from debug_toolbar.decorators import require_show_toolbar
from debug_toolbar.panels.sql import SQLPanel
from debug_toolbar.panels.sql.forms import SQLSelectForm
from django.urls import re_path
from django.http import HttpResponseBadRequest, JsonResponse
from django.template.response import SimpleTemplateResponse
from django.template.loader import render_to_string
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_exempt
from debug_toolbar.panels.sql.views import get_signed_data
import requests
import re
class PevSQLPanel(SQLPanel):
    template = 'pev_sql/sql_panel.html'

    @classmethod
    def get_urls(cls):
        return super().get_urls() + [
            re_path(r'^sql_pev/$', sql_pev, name='sql_pev'),
            re_path(r'^pev/$', pev, name='pev'),
        ]


@csrf_exempt
@require_show_toolbar
def sql_pev(request):
    """Returns the output of the SQL EXPLAIN on the given query"""
    signed = get_signed_data(request)
    form = SQLSelectForm(signed or None)
    if not form.is_valid():
        return HttpResponseBadRequest('Form errors')

    sql = form.cleaned_data['raw_sql']
    params = form.cleaned_data['params']
    cursor = form.cursor
    cursor.execute("EXPLAIN (ANALYZE, VERBOSE, BUFFERS, FORMAT JSON) %s" % (sql,), params)
    plan, = cursor.fetchone()

    post_data = {
        'plan': json.dumps(plan),
        'title': request.path, #XXX######################################################################################
        'query': sql,
    }
    response = requests.post('https://explain.dalibo.com/new', data=post_data)
    url = re.findall(r'<a href="\/plan/(.+)"', response.text)[0]
    content = render_to_string("pev_sql/pev_wrapper.html", {"url": url})
    return JsonResponse({"content": content})


@xframe_options_sameorigin
@csrf_exempt
@require_show_toolbar
def pev(request):
    """Displays the Postgres Explain Visualizer using the EXPLAIN from sql_pev
    """
    # Disable the DJDT toolbar in our iframe
    from debug_toolbar.middleware import DebugToolbarMiddleware
    #DebugToolbarMiddleware.debug_toolbars[threading.current_thread().ident] = None

    # Using SimpleTemplateResponse avoids running global context processors.
    return SimpleTemplateResponse('pev_sql/pev.html')
