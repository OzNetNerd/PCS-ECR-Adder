# Prisma Cloud: ECR Adder

This scripts automates the process of adding ECR registry scanning to Prisma Cloud.

## Required Parameters

The script requires 3 parameters. Each are described below.


### PRISMA_CLOUD_URL

The `--prisma-cloud-url <PRISMA_CLOUD_URL>` flag is used to specify your tenancy's URL. It can be found in "Compute" -> "System" -> "Utilities".

### REGIONS

Each AWS account has one ECR registry per region. Use the `--regions <REGIONS>` flag to specify the regions you'd like to scan.

If you'd like to scan all regions, the command below provides an up-to-date list of EC2 regions:

```
aws ec2 describe-regions --all-regions --query "Regions[].{Name:RegionName}" --output text
```

### DUPLICATE_ENTRIES

The `--duplicate-entries` flag accepts only `Y` or `N` as input. Entering `Y` will add all registries that are listed in your CSV file, even if there are existing entries for it in Prisma Cloud. Conversely, entering `N` will cause the script to skip registries which already have entries in Prisma Cloud. 

Note: The script looks for duplicates on a per account, per-region basis. This ensures that all specified registries will have coverage.  

```
 python ecradder.py -h 
usage: ecradder.py [-h] -u PRISMA_CLOUD_URL -d DUPLICATE_ENTRIES -r REGIONS

Prisma CLoud ECR Adder

options:
  -h, --help            show this help message and exit
  -u PRISMA_CLOUD_URL, --prisma-cloud-url PRISMA_CLOUD_URL
                        Prisma Cloud API URL. It can be found in "Compute" -> "System" -> "Utilities"
  -d DUPLICATE_ENTRIES, --duplicate-entries DUPLICATE_ENTRIES
                        Allow duplicate entries: Y or N
  -r REGIONS, --regions REGIONS
                        Comma separated list of regions to scan, e.g: ap-southeast-1,ap-southeast-2
```

## Configuration CSV file

The configuration CSV file must be located in the same directory as the script. It must also contain the following fields:
* accountId: AWS account ID
* credentialId: Prisma Cloud "Credential" ID that has the necessary permissions to access the specified AWS account ID 
* collection: A collection that contains the hosts that will be used to scan the specified AWS account's registry/registries   
* osType: The base OS of the registry images. At the time of writing, the options are `linux`,`linuxARM64` and `windows`. See the [API docs](https://prisma.pan.dev/api/cloud/cwpp/) for the latest information  
* scanners: The number of Defenders that can be utilised for each scan job

## Example usage

This example will use this CSV file:

```
accountId,credentialId,collection,osType,scanners
111111111111,Will Robinson - AWS Cloud,Will-R-Ecr-Scanner-Collection,linux,2
222222222222,Will Robinson - AWS Cloud,Will-R-Ecr-Scanner-Collection,linux,2
```

Before executing the script, the Prisma Cloud API token must be retrieved from "Compute" -> "System" -> "Utilities". The script then can be executed across all regions of interest, like so:

```
python ecradder.py --prisma-cloud-url https://us-east1.cloud.twistlock.com/us-1-111234567 --duplicate-entries N --regions ap-south-2,ap-south-1,eu-south-1,eu-south-2,me-central-1,ca-central-1,eu-central-1,eu-central-2,us-west-1,us-west-2,af-south-1,eu-north-1,eu-west-3,eu-west-2,eu-west-1,ap-northeast-3,ap-northeast-2,me-south-1,ap-northeast-1,sa-east-1,ap-east-1,ap-southeast-1,ap-southeast-2,ap-southeast-3,us-east-1,us-east-2
```

The following command was used for the purposes of this example:

```
python ecradder.py --prisma-cloud-url https://us-east1.cloud.twistlock.com/us-1-111234567 --duplicate-entries N --regions ap-south-2,ap-south-1,eu-south-1,eu-south-2,me-central-1
```

The script then requests your API token:

```
API token:
```

It will then connect to and scan all of your specified registry:

```
Found Account ID "111111111111". Adding registries in the specified regions:
Checking "111111111111.dkr.ecr.eu-south-1.amazonaws.com"...
Successfully added new registry.
Checking "111111111111.dkr.ecr.ap-south-1.amazonaws.com"...
Successfully added new registry.
Checking "111111111111.dkr.ecr.eu-south-2.amazonaws.com"...
Successfully added new registry.
Checking "111111111111.dkr.ecr.ap-south-2.amazonaws.com"...
Successfully added new registry.
Checking "111111111111.dkr.ecr.me-central-1.amazonaws.com"...
Successfully added new registry.

Found Account ID "222222222222". Adding registries in the specified regions:
Checking "222222222222.dkr.ecr.eu-south-1.amazonaws.com"...
Successfully added new registry.
Checking "222222222222.dkr.ecr.ap-south-1.amazonaws.com"...
Successfully added new registry.
Checking "222222222222.dkr.ecr.eu-south-2.amazonaws.com"...
Successfully added new registry.
Checking "222222222222.dkr.ecr.ap-south-2.amazonaws.com"...
Successfully added new registry.
Checking "222222222222.dkr.ecr.me-central-1.amazonaws.com"...
Successfully added new registry.

****************************************************************************************************

10 NEW REGISTRIES ADDED:
1. 111111111111.dkr.ecr.eu-south-1.amazonaws.com
2. 222222222222.dkr.ecr.me-central-1.amazonaws.com
3. 222222222222.dkr.ecr.eu-south-2.amazonaws.com
4. 111111111111.dkr.ecr.ap-south-2.amazonaws.com
5. 222222222222.dkr.ecr.ap-south-1.amazonaws.com
6. 111111111111.dkr.ecr.me-central-1.amazonaws.com
7. 222222222222.dkr.ecr.eu-south-1.amazonaws.com
8. 222222222222.dkr.ecr.ap-south-2.amazonaws.com
9. 111111111111.dkr.ecr.eu-south-2.amazonaws.com
10. 111111111111.dkr.ecr.ap-south-1.amazonaws.com

0 DUPLICATE REGISTRIES (SKIPPED):
N/A

0 REGISTRIES THAT EXPERIENCED ERRORS:
N/A

****************************************************************************************************
Successfully added 10 registries across 2 accounts and 5 regions.
0 duplicate registries were found and skipped.
****************************************************************************************************
```
