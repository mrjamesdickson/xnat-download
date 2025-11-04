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
parser.add_argument('--download', required=False, type=str, default='both', choices=['experiments', 'assessors', 'both'], dest='download_mode', help='What to download: experiments, assessors, or both (default: both)')
parser.add_argument('--experiment-type', required=False, type=str,dest='xnat_experiment_type', help='XNAT experiment type filter (e.g., xnat:mrSessionData, xnat:petSessionData)')
parser.add_argument('--assessor-type', required=False, type=str,dest='xnat_assessor_type', help='XNAT assessor type filter (e.g., icr:RoiCollection)')

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
            mySubject = myProject.subjects[mySubjectID]
            myExperimentsList = mySubject.experiments.values()

            subject_has_data = False

            # Process experiments
            for e in myExperimentsList:

                myExperimentID = e.label
                myExperimentType = type(e).__name__ if not hasattr(e, 'xsi_type') else e.xsi_type

                # Filter by session label if specified
                if args.xnat_session and myExperimentID != args.xnat_session:
                    continue

                # Download experiments if mode allows
                if args.download_mode in ['experiments', 'both']:
                    # Filter by experiment type if specified
                    if args.xnat_experiment_type:
                        if myExperimentType != args.xnat_experiment_type:
                            print(f'Skipping experiment {myExperimentID} - type {myExperimentType} does not match filter {args.xnat_experiment_type}')
                        else:
                            print(f'✓ Match found: {myExperimentID} - type {myExperimentType} matches filter {args.xnat_experiment_type}')
                            print('\nEntering experiment ...' + myExperimentID + ' (type: ' + myExperimentType + ')')

                            # Create subject directory only when we have data to download
                            if not subject_has_data:
                                if os.path.exists(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID) == False:
                                    os.makedirs(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID)
                                subject_has_data = True

                            myExperiment = mySubject.experiments[myExperimentID]
                            myzip=  myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID + '/' + myExperimentID + '.zip'

                            if os.path.exists(myzip):
                                print("skipping",myzip)
                            else:
                                myExperiment.download(myzip)
                    else:
                        # No type filter, download all experiments
                        print('\nEntering experiment ...' + myExperimentID + ' (type: ' + myExperimentType + ')')

                        # Create subject directory only when we have data to download
                        if not subject_has_data:
                            if os.path.exists(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID) == False:
                                os.makedirs(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID)
                            subject_has_data = True

                        myExperiment = mySubject.experiments[myExperimentID]
                        myzip=  myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID + '/' + myExperimentID + '.zip'

                        if os.path.exists(myzip):
                            print("skipping",myzip)
                        else:
                            myExperiment.download(myzip)

                # Process assessors for this experiment if mode allows
                if args.download_mode in ['assessors', 'both']:
                    myExperiment = mySubject.experiments[myExperimentID]
                    myAssessorsList = myExperiment.assessors.values()
                    for a in myAssessorsList:
                        myAssessorID = a.label
                        myAssessorType = type(a).__name__ if not hasattr(a, 'xsi_type') else a.xsi_type

                        # Filter by assessor type if specified
                        if args.xnat_assessor_type:
                            if myAssessorType != args.xnat_assessor_type:
                                print(f'Skipping assessor {myAssessorID} - type {myAssessorType} does not match filter {args.xnat_assessor_type}')
                                continue
                            else:
                                print(f'✓ Match found: {myAssessorID} - type {myAssessorType} matches filter {args.xnat_assessor_type}')

                        print('\nEntering assessor ...' + myAssessorID + ' (type: ' + myAssessorType + ')')

                        # Create subject directory only when we have data to download
                        if not subject_has_data:
                            if os.path.exists(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID) == False:
                                os.makedirs(myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID)
                            subject_has_data = True

                        myAssessor = myExperiment.assessors[myAssessorID]
                        myzip=  myWorkingDirectory + '/' + myProjectID + '/' + mySubjectID + '/' + myAssessorID + '.zip'

                        if os.path.exists(myzip):
                            print("skipping",myzip)
                        else:
                            myAssessor.download(myzip)
    return
#
print(VERSION)
#
#
xnat_collection(myWorkingDirectory,collectionURL,myProjectID)