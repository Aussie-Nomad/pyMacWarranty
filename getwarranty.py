#!/usr/bin/env python

import sys, json, subprocess, datetime

try:
    import requests
except:
    # My strange hack to use standard libs, if requests module isn't available
    # http://docs.python-requests.org/en/latest/index.html
    # Really, check it out - it's great
    import urllib, types
    import urllib2 as requests
    setattr(requests,'content','')
    def get(self, urlstr, params={}):
        if (params):
            urlstr += "?%s" % urllib.urlencode(params)
        self.content = self.urlopen(urlstr).read()
        return self
    requests.get = types.MethodType(get,requests)

standard_keys = (('PROD_DESCR', 'Product Description'),
                 ('SERIAL_ID', 'Serial Number'),
                 ('HW_COVERAGE_DESC', 'Warranty Type'),
                 ('EST_MANUFACTURED_DATE', 'Estimated Manufacture Date'))

asd_db = {}

def init_asd_db():
    if (not asd_db):
        response = requests.get('https://raw.github.com/stefanschmidt/warranty/master/asdcheck')
        for model,val in [model_str.strip().split(':') for model_str in response.content.split('\n') if model_str.strip()]:
            asd_db[model] = val

def warranty_json(sn, country='US'):
    return json.loads(requests.get('https://selfsolve.apple.com/warrantyChecker.do', params={'country': country, 'sn': sn}).content[5:-1])

def coverage_date(details):
    coverage = 'EXPIRED'
    if (details.has_key('COV_END_DATE') and (details['COV_END_DATE'] != u'')):
        coverage = 'COV_END_DATE'
    if (details.has_key('HW_END_DATE')):
        coverage = 'HW_END_DATE'
    return (coverage, 'Coverage')

def asd_version(details):
    init_asd_db()
    return (asd_db.get(details['PROD_DESCR'], 'Not found')+"\n", 'ASD Version')

def get_estimated_manufacture(serial):
    est_date = u''
    if 10 < len(serial) < 13:
        if len(serial) == 11:
            # Old format
            year = serial[2].lower()
            est_year = 2000 + ' 1234567890'.index(year)
            week = int(serial[3:5]) - 1
            year_time = datetime.date(year=est_year, month=1, day=1)
            if (week):
                week_dif = datetime.timedelta(weeks=week)
                year_time += week_dif
            est_date = u'' + year_time.isoformat()
        else:
            # New format
            alpha_year = 'cdfghjklmnpqrstvwxyz'
            year = serial[3].lower()
            est_year = str(2010 + (alpha_year.index(year) / 2))
            # 1st or 2nd half of the year
            est_half = alpha_year.index(year) % 2
            week = serial[4].lower()
            alpha_week = ' 123456789cdfghjklmnpqrtvwxy'
            est_week = alpha_week.index(week) + (est_half * 26) - 1
            year_time = datetime.date(year=est_year, month=1, day=1)
            if (est_week):
                week_dif = datetime.timedelta(weeks=est_week)
                year_time += week_dif
            est_date = u'' + year_time.isoformat()
    return est_date

def get_warranty(*serials):
    for serial in serials:
        info = warranty_json(serial)
        if (info.has_key('ERROR_CODE')):
            print "ERROR: Invalid serial: %s\n" % (serial)
        else:
            info[u'EST_MANUFACTURED_DATE'] = get_estimated_manufacture(serial)
            for key,label in (standard_keys + (coverage_date(info), asd_version(info))):
                print "%s: %s" % (label, info.get(key, key))

def get_warranty_dict(serial):
    info = warranty_json(serial)
    if (info.has_key('ERROR_CODE')):
        return None
    else:
        info[u'EST_MANUFACTURED_DATE'] = get_estimated_manufacture(serial)
        return info

def get_my_serial():
    return [x for x in [subprocess.Popen("system_profiler SPHardwareDataType |grep -v tray |awk '/Serial/ {print $4}'", shell=True, stdout=subprocess.PIPE).communicate()[0].strip()] if x]

def main():
    for serial in (sys.argv[1:] or get_my_serial()):
        get_warranty(serial)
        
if __name__ == "__main__":
    main()

