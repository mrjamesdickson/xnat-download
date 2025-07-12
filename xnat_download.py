# -*- coding: utf-8 -*-
"""
@author: JDickson
"""


#this needs the xnat package installed i.e.
#pip install xnat
import xnat
import os
import subprocess
import argparse
import os.path
import getpass
import requests

from requests.auth import HTTPBasicAuth

parser = argparse.ArgumentParser()
parser.add_argument('--output',required = True,dest='output',help='Path to the output directory')
parser.add_argument('--user', required=True,type=str,dest='xnat_user', help='XNAT username')
parser.add_argument('--pass',type=str,dest='xnat_pass', help='XNAT password')
parser.add_argument('--host',  required=True,type=str,dest='xnat_host', help='XNAT hostname')
parser.add_argument('--project', required=True, type=str,dest='xnat_project', help='XNAT project')
parser.add_argument('--session', required=False, type=str,dest='xnat_session', help='XNAT session')

args = parser.parse_args()

VERSION='xnat_download_v1.0'

myWorkingDirectory = args.output 
collectionURL = args.xnat_host 
myProjectID = args.xnat_project 
xnat_session=args.xnat_session 
username=args.xnat_user
password=args.xnat_pass

if password is None:
    password = getpass.getpass("Enter your password: ")



def login(host,username,password):

    basic = HTTPBasicAuth(username, password)
    response=requests.get(host+'/data/JSESSION', auth=basic)
    print(response.content)
    return response.content.decode("utf-8")


# Download data from XNAT in .zip format
def xnat_collection(myWorkingDirectory,collectionURL,myProjectID):
    os.chdir(myWorkingDirectory)
    projDir=myWorkingDirectory + '/' + myProjectID
    if os.path.exists(projDir) == False:
        os.makedirs(projDir)
    print('Downloading project ... ' + myProjectID)
    jsession=login(collectionURL,username,password)

    with xnat.connect(collectionURL,jsession=jsession) as mySession:
        myProject= mySession.projects[myProjectID]
        mySubjectsList = myProject.subjects.values()
        for s in mySubjectsList:
            mySubjectID = s.label
            print('\nEntering subject ...' + mySubjectID)
            if os.path.exists(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID) == False:
                os.makedirs(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID)
            mySubject = myProject.subjects[mySubjectID]
            myExperimentsList = mySubject.experiments.values()

            for e in myExperimentsList:
                
                myExperimentID = e.label 
                if myExperimentID == args.xnat_session or not xnat_session:
                    print('\nEntering experiment ...' + myExperimentID)
                
                    myExperiment = mySubject.experiments[myExperimentID]
                    myzip=  myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID + '/' + myExperimentID + '.zip'
                
                    if os.path.exists(myzip):
                        print("skipping",myzip)
                    else:
                        myExperiment.download(myzip)
    return
#
print(VERSION)
#
#
xnat_collection(myWorkingDirectory,collectionURL,myProjectID)