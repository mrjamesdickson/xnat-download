# XNAT Download

Python script to download experiments and assessors from XNAT servers in ZIP format.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 xnat_download.py --output OUTPUT --user XNAT_USER --host XNAT_HOST --project XNAT_PROJECT [OPTIONS]
```

### Required Arguments

- `--user XNAT_USER` - XNAT username
- `--host XNAT_HOST` - XNAT hostname (e.g., https://xnat.example.com)
- `--project XNAT_PROJECT` - XNAT project ID

### Optional Arguments

- `--output OUTPUT` - Path to the output directory (required unless using --list-types)
- `--pass XNAT_PASS` - XNAT password (if omitted, prompts interactively)
- `--session XNAT_SESSION` - Download only a specific session/experiment label
- `--download {experiments,assessors,both}` - What to download (default: both)
- `--experiment-type XNAT_EXPERIMENT_TYPE` - Filter experiments by type (e.g., xnat:mrSessionData)
- `--assessor-type XNAT_ASSESSOR_TYPE` - Filter assessors by type (e.g., IcrRoiCollectionData)
- `--list-types` - List all experiment and assessor types found in the project and exit (no download)

## Examples

List all available experiment and assessor types in a project:
```bash
python3 xnat_download.py --user admin --host https://xnat.example.com --project MyProject --list-types
```

Download all experiments and assessors from a project:
```bash
python3 xnat_download.py --output ./data --user admin --host https://xnat.example.com --project MyProject
```

Download only assessors of type IcrRoiCollectionData:
```bash
python3 xnat_download.py --output ./data --user admin --host https://xnat.example.com --project MyProject --download assessors --assessor-type IcrRoiCollectionData
```

Download only MR session experiments:
```bash
python3 xnat_download.py --output ./data --user admin --host https://xnat.example.com --project MyProject --download experiments --experiment-type xnat:mrSessionData
```

Download a specific session:
```bash
python3 xnat_download.py --output ./data --user admin --host https://xnat.example.com --project MyProject --session MySession-001
```

## Features

- Downloads experiments and/or assessors from XNAT projects
- Supports type filtering for both experiments and assessors
- Creates directory structure: `output/project/subject/experiment.zip` or `assessor.zip`
- Skips already-downloaded files (resumable downloads)
- Only creates subject directories when matching data is found
- Verbose output showing type matching and filtering

## Output Structure

```
output/
└── ProjectID/
    └── SubjectID/
        ├── ExperimentID.zip
        └── AssessorID.zip
```
