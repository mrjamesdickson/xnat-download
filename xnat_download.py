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
import json
from contextlib import contextmanager

from requests.auth import HTTPBasicAuth

parser = argparse.ArgumentParser()
parser.add_argument('--output',required = False,dest='output',help='Path to the output directory')
parser.add_argument('--user', required=True,type=str,dest='xnat_user', help='XNAT username')
parser.add_argument('--pass',type=str,dest='xnat_pass', help='XNAT password')
parser.add_argument('--host',  required=True,type=str,dest='xnat_host', help='XNAT hostname')
parser.add_argument('--project', required=True, type=str,dest='xnat_project', help='XNAT project ID')
parser.add_argument('--session', required=False, type=str,dest='xnat_session', help='XNAT session/experiment label to download')
parser.add_argument('--download', required=False, type=str, default='both', choices=['experiments', 'assessors', 'both'], dest='download_mode', help='What to download: experiments, assessors, or both (default: both)')
parser.add_argument('--experiment-type', required=False, type=str,dest='xnat_experiment_type', help='XNAT experiment type filter (e.g., xnat:mrSessionData, xnat:petSessionData)')
parser.add_argument('--assessor-type', required=False, type=str,dest='xnat_assessor_type', help='XNAT assessor type filter (e.g., icr:RoiCollection)')
parser.add_argument('--list-types', required=False, action='store_true', dest='list_types', help='List all experiment and assessor types found in the project and exit')

args = parser.parse_args()

VERSION='xnat_download_v1.1.1'

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


@contextmanager
def xnat_session_safe(collectionURL, jsession):
    """Context manager that safely handles XNAT session disconnect errors"""
    session = xnat.connect(collectionURL, jsession=jsession)
    try:
        yield session
    finally:
        try:
            session.disconnect()
        except Exception as e:
            # Ignore disconnect errors - session is ending anyway
            print(f"Note: Session disconnect error (ignoring): {e}")


def download_with_retry(download_func, filepath, max_retries=3):
    """Download with retry logic for session timeout errors"""
    for attempt in range(max_retries):
        try:
            download_func(filepath)
            return True
        except Exception as e:
            if '401' in str(e) or 'Unauthorized' in str(e):
                if attempt < max_retries - 1:
                    print(f"  Session timeout, retrying ({attempt + 1}/{max_retries})...")
                    # Re-login will happen on next iteration of main loop
                    raise  # Re-raise to trigger session refresh
                else:
                    print(f"  Failed after {max_retries} attempts: {e}")
                    raise
            else:
                # Non-auth error, don't retry
                raise
    return False


# List all types in project
def list_types(collectionURL,myProjectID):
    print('Scanning project ... ' + myProjectID)
    jsession=login(collectionURL,username,password)

    experiment_types = set()
    assessor_types = set()

    with xnat_session_safe(collectionURL, jsession) as mySession:
        myProject= mySession.projects[myProjectID]
        mySubjectsList = myProject.subjects.values()
        for s in mySubjectsList:
            mySubjectID = s.label
            mySubject = myProject.subjects[mySubjectID]
            myExperimentsList = mySubject.experiments.values()

            for e in myExperimentsList:
                myExperimentType = type(e).__name__ if not hasattr(e, 'xsi_type') else e.xsi_type
                experiment_types.add(myExperimentType)

                myExperiment = mySubject.experiments[e.label]
                myAssessorsList = myExperiment.assessors.values()
                for a in myAssessorsList:
                    myAssessorType = type(a).__name__ if not hasattr(a, 'xsi_type') else a.xsi_type
                    assessor_types.add(myAssessorType)

    print('\nExperiment types found:')
    for exp_type in sorted(experiment_types):
        print(f'  {exp_type}')

    print('\nAssessor types found:')
    if assessor_types:
        for ass_type in sorted(assessor_types):
            print(f'  {ass_type}')
    else:
        print('  (none)')

    return

# Download data from XNAT in .zip format
def xnat_collection(myWorkingDirectory,collectionURL,myProjectID):
    # Create output directory if it doesn't exist
    if not os.path.exists(myWorkingDirectory):
        os.makedirs(myWorkingDirectory)
        print(f'Created output directory: {myWorkingDirectory}')
    os.chdir(myWorkingDirectory)
    projDir=myWorkingDirectory + '/' + myProjectID
    if os.path.exists(projDir) == False:
        os.makedirs(projDir)
    print('Downloading project ... ' + myProjectID)

    # Track progress
    progress_file = os.path.join(projDir, '.download_progress.json')
    download_stats = {'subjects_processed': 0, 'files_downloaded': 0, 'files_skipped': 0, 'last_subject': None}

    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                download_stats = json.load(f)
            print(f"Resuming from subject: {download_stats['last_subject']}")
            print(f"Previously: {download_stats['subjects_processed']} subjects, {download_stats['files_downloaded']} downloaded, {download_stats['files_skipped']} skipped")
        except:
            pass

    # Process in batches with session refresh every 100 subjects
    batch_size = 100
    session_refresh_count = 0

    jsession = login(collectionURL, username, password)

    with xnat_session_safe(collectionURL, jsession) as mySession:
        myProject= mySession.projects[myProjectID]
        mySubjectsList = myProject.subjects.values()
        for subject_idx, s in enumerate(mySubjectsList):
            mySubjectID = s.label

            # Refresh session every batch_size subjects to prevent timeout
            if subject_idx > 0 and subject_idx % batch_size == 0:
                session_refresh_count += 1
                print(f"\n[Session Refresh {session_refresh_count}] Refreshing login after {subject_idx} subjects...")
                # Close current session and reconnect
                try:
                    mySession.disconnect()
                except:
                    pass
                jsession = login(collectionURL, username, password)
                mySession = xnat.connect(collectionURL, jsession=jsession)
                myProject = mySession.projects[myProjectID]
                print("[Session Refresh] Reconnected successfully")

            print('\nEntering subject ...' + mySubjectID)

            # Build list of experiments/assessors to check before making API calls
            subject_dir = os.path.join(myWorkingDirectory, myProjectID, mySubjectID)
            existing_files = set()
            if os.path.exists(subject_dir):
                existing_files = set(os.listdir(subject_dir))

            mySubject = myProject.subjects[mySubjectID]
            myExperimentsList = mySubject.experiments.values()

            subject_has_data = False
            subject_downloaded = 0
            subject_skipped = 0

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
                    if args.xnat_experiment_type and myExperimentType != args.xnat_experiment_type:
                        continue

                    # Check if already downloaded before accessing XNAT API
                    experiment_filename = myExperimentID + '.zip'
                    if experiment_filename in existing_files:
                        subject_skipped += 1
                        print(f'(skip) {myExperimentID} - already downloaded')
                        subject_has_data = True
                    else:
                        if args.xnat_experiment_type:
                            print(f'✓ Match found: {myExperimentID} - type {myExperimentType} matches filter {args.xnat_experiment_type}')
                        print('Downloading experiment: ' + myExperimentID + ' (type: ' + myExperimentType + ')')

                        # Create subject directory only when we have data to download
                        if not subject_has_data:
                            if not os.path.exists(subject_dir):
                                os.makedirs(subject_dir)
                            subject_has_data = True

                        myExperiment = mySubject.experiments[myExperimentID]
                        myzip = os.path.join(subject_dir, experiment_filename)

                        # Retry download with session refresh on 401
                        download_success = False
                        for retry_attempt in range(3):
                            try:
                                myExperiment.download(myzip)
                                subject_downloaded += 1
                                print(f'✓ Downloaded: {experiment_filename}')
                                download_success = True
                                break
                            except Exception as e:
                                if '401' in str(e) or 'Unauthorized' in str(e):
                                    print(f'✗ Session expired, refreshing and retrying (attempt {retry_attempt + 1}/3)...')
                                    # Refresh session
                                    try:
                                        mySession.disconnect()
                                    except:
                                        pass
                                    jsession = login(collectionURL, username, password)
                                    mySession = xnat.connect(collectionURL, jsession=jsession)
                                    myProject = mySession.projects[myProjectID]
                                    mySubject = myProject.subjects[mySubjectID]
                                    myExperiment = mySubject.experiments[myExperimentID]
                                    # Retry download on next loop iteration
                                else:
                                    print(f'✗ Error downloading {experiment_filename}: {e}')
                                    break  # Don't retry non-auth errors

                # Process assessors for this experiment if mode allows
                if args.download_mode in ['assessors', 'both']:
                    myExperiment = mySubject.experiments[myExperimentID]
                    myAssessorsList = myExperiment.assessors.values()
                    for a in myAssessorsList:
                        myAssessorID = a.label
                        myAssessorType = type(a).__name__ if not hasattr(a, 'xsi_type') else a.xsi_type

                        # Filter by assessor type if specified
                        if args.xnat_assessor_type and myAssessorType != args.xnat_assessor_type:
                            continue

                        # Check if already downloaded before accessing XNAT API
                        assessor_filename = myAssessorID + '.zip'
                        if assessor_filename in existing_files:
                            subject_skipped += 1
                            print(f'(skip) {myAssessorID} - already downloaded')
                            subject_has_data = True
                        else:
                            if args.xnat_assessor_type:
                                print(f'✓ Match found: {myAssessorID} - type {myAssessorType} matches filter {args.xnat_assessor_type}')
                            print('Downloading assessor: ' + myAssessorID + ' (type: ' + myAssessorType + ')')

                            # Create subject directory only when we have data to download
                            if not subject_has_data:
                                if not os.path.exists(subject_dir):
                                    os.makedirs(subject_dir)
                                subject_has_data = True

                            myAssessor = myExperiment.assessors[myAssessorID]
                            myzip = os.path.join(subject_dir, assessor_filename)

                            # Retry download with session refresh on 401
                            download_success = False
                            for retry_attempt in range(3):
                                try:
                                    myAssessor.download(myzip)
                                    subject_downloaded += 1
                                    print(f'✓ Downloaded: {assessor_filename}')
                                    download_success = True
                                    break
                                except Exception as e:
                                    if '401' in str(e) or 'Unauthorized' in str(e):
                                        print(f'✗ Session expired, refreshing and retrying (attempt {retry_attempt + 1}/3)...')
                                        # Refresh session
                                        try:
                                            mySession.disconnect()
                                        except:
                                            pass
                                        jsession = login(collectionURL, username, password)
                                        mySession = xnat.connect(collectionURL, jsession=jsession)
                                        myProject = mySession.projects[myProjectID]
                                        mySubject = myProject.subjects[mySubjectID]
                                        myExperiment = mySubject.experiments[myExperimentID]
                                        myAssessor = myExperiment.assessors[myAssessorID]
                                        # Retry download on next loop iteration
                                    else:
                                        print(f'✗ Error downloading {assessor_filename}: {e}')
                                        break  # Don't retry non-auth errors

            # Update progress after each subject
            download_stats['subjects_processed'] += 1
            download_stats['files_downloaded'] += subject_downloaded
            download_stats['files_skipped'] += subject_skipped
            download_stats['last_subject'] = mySubjectID

            # Save progress checkpoint every 10 subjects
            if download_stats['subjects_processed'] % 10 == 0:
                with open(progress_file, 'w') as f:
                    json.dump(download_stats, f)
                print(f"\n[Progress] Subjects: {download_stats['subjects_processed']}, Downloaded: {download_stats['files_downloaded']}, Skipped: {download_stats['files_skipped']}")

    # Final progress save
    with open(progress_file, 'w') as f:
        json.dump(download_stats, f)
    print(f"\n[Complete] Total subjects: {download_stats['subjects_processed']}, Downloaded: {download_stats['files_downloaded']}, Skipped: {download_stats['files_skipped']}")
    return
#
print(VERSION)
#
#
if args.list_types:
    list_types(collectionURL,myProjectID)
else:
    if not args.output:
        print("Error: --output is required when downloading data")
        exit(1)
    xnat_collection(myWorkingDirectory,collectionURL,myProjectID)