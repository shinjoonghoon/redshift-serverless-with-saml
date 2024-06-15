# sql-workbench

https://docs.aws.amazon.com/ko_kr/redshift/latest/mgmt/connecting-using-workbench.html

https://www.sql-workbench.eu/downloads.html


## Manager Drivers

- [Redshift JDBC driver 다운로드](https://s3.amazonaws.com/redshift-downloads/drivers/jdbc/2.1.0.28/redshift-jdbc42-2.1.0.28.zip)
- Redshift JDBC driver 압축 풀기

- Name: `Redshift`
- Library: `jars 선택`
- Classname: `com.amazon.redshift.jdbc42.Driver`

## New connection

- Driver 선택: `Redshift`

- URL
  ```
  jdbc:redshift:iam://[Redshift Serverless Endpoint address]:[Redshift Serverless Endpoint port]/[database]
  ```

  - Redshift Serverless Endpoint 정보 조회
    ```
    aws redshift-serverless get-workgroup --workgroup-name newbank-serverless-workgroup --query 'workgroup.endpoint.{address: address, port: port}' --output json
    ```

  ```
  jdbc:redshift:iam://newbank-serverless-workgroup.account-id.ap-northeast-2.redshift-serverless.amazonaws.com:5454/dev
  ```

## Extended Propreties

- `login_url`: `https://[Keycloak PrivateDnsName]:8081/realms/newbankrealm/protocol/saml/clients/signin`
  - Keycloak PrivateDnsName 조회
  ```
  aws ec2 describe-instances \
  --filters "Name=tag:Name,Values='Keycloak'" \
  --query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
  ```

- `plugin_name`: `plugin_name	com.amazon.redshift.plugin.BrowserSamlCredentialsProvider`
- `ssl_insecure`: `true`
- `idp_response_timeout`: `60`

---

