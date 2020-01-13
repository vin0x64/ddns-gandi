#!/usr/bin/python3

#import socket
import requests
import json
import logging
import argparse
import configparser

#configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger=logging.getLogger('ddns-gandi')

#
# global config
#
gandi_enpoint = 'https://api.gandi.net/v5'
default_conf = "ddns-gandi.conf"

#
# get my ip from external API
#
def get_external_ip():
    url_ipfy = "https://api.ipify.org"
    try:
        r=requests.get(url_ipfy)
        my_ip = r.text
        logger.debug("My IP: "+my_ip)
    except:
        logger.exception("Could not find my ip\n" + r.text)
        my_ip = None
    return my_ip

#
# get content of A record
#
def get_gandi_A_record(apikey, domain, name):
    logger.debug("get_gandi_A_record(): API: %s domain: %s name: %s" %(apikey, domain, name))
    try:
        r = requests.get(gandi_enpoint+"/livedns/domains/%s/records/%s/A" %(domain, name),
                     headers={'Authorization': 'Apikey '+apikey}
                     )
        logger.debug("Gandi's answer JSON:\n"+str(r.json()))
        rrset=r.json()
        my_gandi_ip=''
        ## add logic if A record does not exist yet
        if rrset['rrset_type'] == 'A':
            my_gandi_ip=rrset['rrset_values'][0]
        logger.debug("Gandi's ip for %s : %s" %(my_hostname, my_gandi_ip))
    except:
        logger.exception("Error trying to get Gandi's IP\n"+r.text)
        my_gandi_ip=None
    return my_gandi_ip


#
# Main program
#
if __name__ == '__main__':
    conf_file = default_conf

    # handle command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', dest='debug', action='store_true')
    parser.add_argument('-c', dest='config', type=str)
    args=parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG)
    if args.config:
        conf_file = args.config

    # read configuration from file; exit in case something is missing/wrong
    logger.debug("config file : " + conf_file)
    config = configparser.ConfigParser()
    config.read(conf_file)
    logger.debug(config.sections())
    if len(config.sections()) == 0:
        logger.exception("Error reading configuration file : " +conf_file)
        exit(255)  
    try:
        my_hostname_list = json.loads(config.get('ddns', 'hosts'))
        my_domain = config.get('ddns', 'domain')
        my_apikey = config.get('ddns', 'apikey')
    except:
        logger.exception("Error reading config file")
        exit(255)


    # check external IP (exit if None)
    my_ip=get_external_ip()
    if my_ip is None:
        exit(255)

    # update dns records for each hostname
    for my_hostname in my_hostname_list:
        # get my ip's record from GANDI Zone
        my_gandi_ip = get_gandi_A_record(my_apikey, my_domain, my_hostname)

        # if different then update gandi's reccord
        if my_gandi_ip == my_ip:
            logger.debug("Zone record OK : %s %s" %(my_hostname+'.'+my_domain, my_ip))
        else:
            logger.debug("Zone reccord differs: '%s' != '%s'; going to update" %(my_ip, my_gandi_ip))
            try:
                # using path to update a single A record for a given record
                r = requests.put(gandi_enpoint + "/livedns/domains/%s/records/%s/A" % (my_domain, my_hostname),
                                 headers={'Authorization': 'Apikey ' + my_apikey},
                                 json={'rrset_type': 'A', 'rrset_values': [my_ip], 'rrset_ttl': 300}
                                 )
                logger.debug("API response: "+r.text)
            except:
                logger.exception("Could not update Gandi's record\n"+r.text)
            #check whther update was successful
            try:
                r = requests.get(gandi_enpoint+"/livedns/domains/%s/records/%s" %(my_domain, my_hostname),
                                 headers={'Authorization': 'Apikey '+my_apikey}
                                 )
                logger.debug("API response: "+r.text)
                my_gandi_ip = r.json()[0]['rrset_values'][0]
                logger.debug("New ip at Gandi for %s : %s" %(my_hostname, my_gandi_ip))
            except:
                logger.exception("Could not check updated value at Gandi's\n"+r.text)




