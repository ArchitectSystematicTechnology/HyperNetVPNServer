#!/usr/bin/env python

# Initialize ES index templates, after having waited for ES to be ready.

from __future__ import print_function

import glob
import json
import optparse
import os
import urllib2
import sys
import time


# Default index settings that are applied to indices that already
# exist. This way we solve the race condition between the creation of
# index templates and the auto-creation of indices triggered by
# rsyslog.
INDEX_SETTINGS = '''
{
  "index": {
    "number_of_replicas": 0,
    "refresh_interval": "30s",
    "merge.scheduler.max_thread_count": 1
  }
}
'''


def wait_for_es(url, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = json.load(
                urllib2.urlopen('%s/_cluster/health?wait_for_status=yellow&timeout=%ds' % (
                    url, timeout)))
            if resp['status'] in ('yellow', 'green'):
                return True
        except Exception as e:
            print('error: %s' % (str(e),))
            pass
        print('ES still not up, waiting...')
        time.sleep(2)
    print('ES was not ready after %d seconds' % (timeout,))
    return False


def load_index_template(url, tplfile):
    with open(tplfile, 'r') as fd:
        tpldata = fd.read()
    name = os.path.splitext(os.path.basename(tplfile))[0]
    req = urllib2.Request(
        '%s/_template/%s' % (url, name),
        headers={'Content-Type': 'application/json'},
        data=tpldata)
    req.get_method = lambda: 'PUT'
    try:
        urllib2.urlopen(req)
        return True
    except urllib2.HTTPError as e:
        print(e.read())
        return False


def update_index_settings(url, index_name):
    req = urllib2.Request(
        '%s/%s/_settings' % (url, index_name),
        headers={'Content-Type': 'application/json'},
        data=INDEX_SETTINGS)
    req.get_method = lambda: 'PUT'
    try:
        urllib2.urlopen(req)
        return True
    except urllib2.HTTPError as e:
        print(e.read())
        return False


def update_existing_indices(url):
    try:
        index_data = json.load(urllib2.urlopen('%s/_all' % url))
    except urllib2.HTTPError as e:
        print(e.read())
        return False
    for index_name in index_data.keys():
        # Ignore Kibana.
        if index_name == 'kibana':
            continue
        if not update_index_settings(url, index_name):
            print('error updating index %s' % index_name)
    return True


def main():
    parser = optparse.OptionParser()
    parser.add_option('--url', default='http://localhost:9200',
                      help='Elasticsearch URL')
    parser.add_option('--dir', default='/etc/elasticsearch/templates',
                      help='Directory containing JSON index templates')
    parser.add_option('--wait-timeout', dest='wait_timeout', type='int',
                      default=1800)
    opts, args = parser.parse_args()
    if len(args) > 0:
        parser.error('too many arguments')

    if not wait_for_es(opts.url, opts.wait_timeout):
        return 1

    ret = 0
    for tplfile in glob.glob(os.path.join(opts.dir, '*.json')):
        print('Loading index template %s' % (tplfile,))
        if not load_index_template(opts.url, tplfile):
            ret = 1

    if not update_existing_indices(opts.url):
        ret = 1

    return ret


if __name__ == '__main__':
    sys.exit(main())

