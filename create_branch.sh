#!/usr/bin/env bash

# This script takes a branch number and description and creates a branch


function print_usage
{
  echo "USAGE: $ create_branch -t <ticket number> -d \"<quoted branch description>\""
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

if [[ -z $1 ]]; then
    : # Got no extra args as expected
else
    echo "Got extra arguments. Is your description in quotes?"
    echo "description given: ${DESCRIPTION}"
    echo print_usage; exit 1
fi

# get svn location
source /Users/twilliams/PycharmProjects/caramel_cli_scripts/bash_variables.txt

# Do the things
echo; echo "creating branch: ${BRANCH_NAME}"; echo
echo "commands run are as follows..."
echo "svn copy -m \"branching for CRML-${TICKET_NUMBER}\" ${SVN_LOC}/trunk ${SVN_LOC}/branches/${BRANCH_NAME}"
svn copy -m "branching for CRML-${TICKET_NUMBER}" ${SVN_LOC}/trunk ${SVN_LOC}/branches/${BRANCH_NAME}
echo "cd ~/projects/caramel-api/branches/"
cd ~/projects/caramel-api/branches/
echo "svn co ${SVN_LOC}/branches/${BRANCH_NAME}"
svn co ${SVN_LOC}/branches/${BRANCH_NAME}
echo "cd ${BRANCH_NAME}"
cd ${BRANCH_NAME}
echo "./bin/modules-symlink -c"
./bin/modules-symlink -c
ech "charm ."
charm .
