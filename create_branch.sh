#!/usr/bin/env bash

# This script takes a branch number and description and creates a branch


function print_usage
{
  echo "USAGE: $ create_branch -t <ticket number> -d <branch description> "
}


# Grab variables from command line
while getopts ":t:d:h" opt
do
  case ${opt} in
    t)  TICKET_NUMBER=$OPTARG
        ;;
    d)  DESCRIPTION=$OPTARG
        ;;
    h)  print_usage
        exit 1
        ;;
    \?) echo "Invalid option: -$OPTARG"
        print_usage
        exit 1
        ;;
    :)  echo "-$OPTARG requires a value"
        print_usage
        exit 1
        ;;
  esac
done
shift $((OPTIND - 1))


# Get/fix/error handle the variables
TICKET_NUMBER=${TICKET_NUMBER}
if [[ -z ${TICKET_NUMBER} ]]; then
    echo "Error: Missing ticket number"; print_usage; exit 1
fi
re='^[0-9]+$'
if ! [[ ${TICKET_NUMBER} =~ $re ]] ; then
   echo "Error: Your ticket number '${TICKET_NUMBER}' is not a number" >&2; print_usage; exit 1
fi
DESCRIPTION=${DESCRIPTION// /-}
if [[ -z ${DESCRIPTION} ]]; then
    echo "Error: Missing branch description"; print_usage; exit 1
fi
BRANCH_NAME="twilliams-CRML-${TICKET_NUMBER}-${DESCRIPTION}"


# get svn location
source bash_variables.txt


# Do the things
echo; echo "creating branch: ${BRANCH_NAME}"; echo
svn copy -m "branching for CRML-${TICKET_NUMBER}" ${SVN_LOC}/trunk ${SVN_LOC}/branches/${BRANCH_NAME}
cd ~/projects/caramel-api/branches/
svn co ${SVN_LOC}/branches/${BRANCH_NAME}
cd ${BRANCH_NAME}
./bin/modules-symlink -c
charm .
