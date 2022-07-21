#!/usr/bin/python3

# Imports Kibana dashboards by loading all files with a .json
# extension from a directory.
#
# Export the dashboards you create with the following command:
#
# curl -XGET localhost:5601/api/kibana/dashboards/export?dashboard=<some-dashboard-uuid>
#


import argparse
import glob
import json
import logging
import sys
import time
import urllib.request


DEFAULT_KIBANA_BASE_URL = 'http://localhost:5601'


def wait_for_green_status(kibana_base_url):
    while True:
        try:
            r = json.load(urllib.request.urlopen(kibana_base_url + '/api/status'))
            status = r['status']['overall']['state']
            if status == 'green':
                break
            logging.debug('Kibana status is not green (%s), retrying...', status)
        except Exception as e:
            logging.debug('Kibana is not reachable (%s), retrying...', e)
        time.sleep(1)


def upload_kibana_dashboards(kibana_base_url, jsonArray):
    for obj in jsonArray:
        headers = {
            'kbn-xsrf': 'anything',
            'Content-Type': 'application/json',
        }
        req = urllib.request.Request(
            f'{kibana_base_url}/api/kibana/dashboards/import?force=true',
            data=json.dumps(obj).encode('utf-8'), headers=headers)
        urllib.request.urlopen(req)


def set_default_index(kibana_base_url, index_id):
    req = urllib.request.Request(
        f'{kibana_base_url}/api/kibana/settings/defaultIndex',
        data=json.dumps({'value': index_id}).encode('utf-8'),
        headers={
            'kbn-xsrf': 'anything',
            'Content-Type': 'application/json',
        })
    urllib.request.urlopen(req)


def main():
    parser = argparse.ArgumentParser(
        description='Imports Kibana json dashboard files into Kibana via its REST API.\n\nExample:\n  %s --dir . --kibana-url %s' % (sys.argv[0], DEFAULT_KIBANA_BASE_URL),
        epilog='This is Free Software under the MIT license.\nCopyright 2017 Niklas Hambuechen <mail@nh2.me>',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dir', metavar='path', type=str, default='/etc/kibana/provisioning', help='Path to *.json files to import')
    parser.add_argument('--kibana-url', metavar='url', type=str, default=DEFAULT_KIBANA_BASE_URL, help='Kibana base URL (default ' + DEFAULT_KIBANA_BASE_URL + ')')
    parser.add_argument('--default-index', metavar='id', type=str, help='Default index ID')
    parser.add_argument('--wait', action='store_true', help='Wait indefinitely for Kibana port to up with status green')
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Load JSON file; it contains an array of objects, whose _type field
    # determines what it is and which endpoint we have to hit.
    dashboards = []
    for f in glob.glob(args.dir + '/*.json'):
        with open(f) as fd:
            dashboards.append(json.load(fd))

    if args.wait:
        wait_for_green_status(args.kibana_url)

    upload_kibana_dashboards(args.kibana_url, dashboards)

    if args.default_index:
        set_default_index(args.kibana_url, args.default_index)


if __name__ == '__main__':
    main()
