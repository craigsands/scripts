#!/bin/bash

# The following command must be run with credentials to the Organization root account.
# Typically, it’s convenient to copy the CLI environment variables from within the SSO
# console login page.

usage() {
  cat << EOF
Usage: $0 [-o ORG_NAME] [-r SSO_ROLE_NAME]
EOF
}

organization_name='myorg'
sso_role_name='AWSAdministratorAccess'
while getopts 'hr:s:' flag; do
  case "${flag}" in
    h) usage && exit 0 ;;
    o) organization_name="${OPTARG}" ;;
    r) sso_role_name="${OPTARG}" ;;
    *) exit 1 ;;
  esac
done

: "${AWS_DEFAULT_REGION:=us-east-1}"

for account in $(
  aws organizations list-accounts \
    --query 'sort_by(Accounts, &Name)[?Status==`ACTIVE`].[Id, Name]' \
    | jq -c '.[]' \
    | tr ' ' '-' \
    | tr '[:upper:]' '[:lower:]'
); do
  account_id=$(echo "${account}" | jq -r '.[0]');
  account_name=$(echo "${account}" | jq -r '.[1]');

  aws configure set sso_session "${organization_name}" \
    --profile "${organization_name}-${sso_role_name}-${account_name}"
  aws configure set sso_account_id "${account_id}" \
    --profile "${organization_name}-${sso_role_name}-${account_name}"
  aws configure set sso_role_name "${sso_role_name}" \
    --profile "${organization_name}-${sso_role_name}-${account_name}"
  aws configure set region "${AWS_DEFAULT_REGION}" \
    --profile "${organization_name}-${sso_role_name}-${account_name}"
done