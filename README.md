# redshift-serverless-with-saml
> Redshift Serverless, SAML, Keycloak, DBeaver

---
# 변경 사항

## (2024.06.16) *기본 브라우저 변경 Chrome -> Firefox*
> `BrowserSAMLCredentialsProvider` 플러그인 사용시 기본 브라우저가 `Chrome`인 경우 SSO 인증 과정(`Authentication Redirect`) 중 오류가 발생할 수 있습니다.

---

# VPC 구성

## [YAML](https://github.com/shinjoonghoon/redshift-serverless-with-saml/blob/main/redshift-serverless-with-saml.yaml) 다운로드

- Stack name: `newbank`
- EnvironmentName: `newbank`

## yaml 배포 후 VPC 다이어그램

<img src="images/vpc-cf.png" alt=""></img>


## 환경 변수 정의

```
REGION=$(aws configure get region)
ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
```

```
aws ec2 describe-vpcs --region $REGION  --query 'Vpcs[].{VpcId: VpcId, Tags: Tags[?Key == `Name`].Value | [0]}' --output json | jq '.[]'
```

```
VPC_ID=your-VpcId
```

```
echo $REGION
echo $ACCOUNT
echo $VPC_ID
```

## VPC 정보 조회

```
aws ec2 describe-vpcs --vpc-ids $VPC_ID
```

## 서브넷 정보 조회

```
aws ec2 describe-subnets --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
```

## [VPC Flow Logs 조회 환경 구성](https://docs.aws.amazon.com/ko_kr/athena/latest/ug/vpc-flow-logs.html)

---

# VPC Endpoints 구성

## VPC Endpoints 적용 후 VPC 다이어그램

<img src="images/vpc-endpoints.png" alt=""></img>

## VPC Endpoints 보안 그룹 생성

- Group name: `VPC_ENDPOINT_SG`

```
aws ec2 create-security-group --description "VPC_ENDPOINT_SG" --group-name "VPC_ENDPOINT_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```

## VPC Endpoints 보안 그룹 Ingress 추가

```
aws ec2 authorize-security-group-ingress \
--group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`VPC_ENDPOINT_SG`)].GroupId' --output text) \
--protocol -1 --port -1 --cidr 10.192.0.0/16 \
--output json | jq '.[]'
```

## VPC Endpoints 서브넷 조회

```
aws ec2 describe-subnets \
--filters "Name=tag:Name,Values='newbank VPC Endpoints Private Subnet*'" \
--query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' \
--output text
```

## VPC Endpoints 생성(sts, ssm, ssmmessages, ec2messages)

```
myarray=(
com.amazonaws.$REGION.ssm
com.amazonaws.$REGION.ssmmessages
com.amazonaws.$REGION.ec2messages
com.amazonaws.$REGION.sts
)
for v in "${myarray[@]}"; do
aws ec2 create-vpc-endpoint \
--region $REGION  \
--vpc-endpoint-type Interface \
--vpc-id  $VPC_ID \
--security-group-ids $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`VPC_ENDPOINT_SG`)].GroupId' --output text) \
--subnet-ids $(aws ec2 describe-subnets --filters "Name=tag:Name,Values='newbank VPC Endpoints*'" --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].[SubnetId]' --output text) \
--service-name $v \
--output json | jq '.[]'
done
```

## VPC Endpoints 생성(s3 gateway type)

```
aws ec2 create-vpc-endpoint \
--region $REGION  \
--vpc-endpoint-type Gateway \
--vpc-id  $VPC_ID \
--route-table-ids $(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --region ap-northeast-2 --query 'RouteTables[].RouteTableId' --output text) \
--service-name com.amazonaws.$REGION.s3 \
--output json | jq '.[]'
```

## VPC Endpoints 생성(s3 interface type)

```
aws ec2 create-vpc-endpoint \
--region $REGION  \
--service-name com.amazonaws.$REGION.s3 \
--vpc-id  $VPC_ID \
--subnet-ids $(aws ec2 describe-subnets --filters "Name=tag:Name,Values='newbank VPC Endpoints*'" --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].[SubnetId]' --output text) \
--vpc-endpoint-type Interface  \
--private-dns-enabled  \
--ip-address-type ipv4 \
--dns-options PrivateDnsOnlyForInboundResolverEndpoint=true \
--security-group-ids $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`VPC_ENDPOINT_SG`)].GroupId' --output text) \
--output json | jq '.[]'
```


## VPC Endpoints 조회

```
while true; do 
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" --region $REGION  --query 'VpcEndpoints[].[State,VpcEndpointType,ServiceName]' --output text;
echo `date`; sleep 2; done;
```

## Network Insterfaces 조회

```
aws ec2 describe-network-interfaces --filters "Name=interface-type,Values=vpc_endpoint" "Name=vpc-id,Values=$VPC_ID" \
--query 'NetworkInterfaces[*].{NetworkInterfaceId:NetworkInterfaceId,PrivateIpAddress:PrivateIpAddress, GroupName:Groups[0].GroupName}' --output text
```

---

# Redshift Serverless 구성

> [Availability Zone IDs](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-usage-considerations.html)   
When you configure your Amazon Redshift Serverless instance, open Additional considerations, and make sure that the subnet IDs provided in Subnet contain at least three of the supported Availability Zone IDs.

## Redshift Serverless 배포 후 VPC 다이어그램

<img src="images/redshift-serverless-1.png" alt=""></img>

## Redshift Serverless 보안 그룹 생성

- Group name: `REDSHIFT_SG`

```
aws ec2 create-security-group --description "REDSHIFT_SG" --group-name "REDSHIFT_SG" --vpc-id $VPC_ID --output json | jq '.[]'

```

## Redshift Serverless 보안 그룹 Ingress 추가

```
aws ec2 authorize-security-group-ingress \
--group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`REDSHIFT_SG`)].GroupId' --output text) \
--protocol -1 --port -1 --cidr 10.192.0.0/16 \
--output json | jq '.[]'
```

## Redshift Serverless 생성

- Workgroup name:  `newbank-serverless-workgroup`
- Base capacity: `32`
- Virtual private cloud (VPC): `newbank`
- VPC security groups: GroupName: `REDSHIFT_SG`
    ```
    aws ec2 describe-security-groups \
    --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`REDSHIFT_SG`)].GroupId' \
    --output text
    ```
- Subnet
    ```
    aws ec2 describe-subnets \
    --filters "Name=tag:Name,Values='newbank Redshift Private Subnet*'" \
    --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' \
    --output text
    ```
- Turn on enhanced VPC routing
- Next
- Namespace: `newbank-serverless-namespace`
- Customize admin user credentials
- Admin user name: `admin`
- Admin user password: Manually add the admin password(secretsmanager 사용 고려)
- Permissions > Associated IAM roles (0) --> No resoureces
- Encryption and security > Export these logs > User log, Connection log, User activity log
- Next
- Review and create
- Create


## Workgroup Status 확인

```
while true; do 
aws redshift-serverless get-workgroup --workgroup-name newbank-serverless-workgroup --query 'workgroup.status'     
echo `date`; sleep 2; done;
```

## Namespace Status 확인

```
while true; do 
aws redshift-serverless get-namespace --namespace-name newbank-serverless-namespace --query 'namespace.status'     
echo `date`; sleep 2; done;
```

## [기본 Port 변경](https://docs.aws.amazon.com/ko_kr/redshift/latest/mgmt/serverless-connecting.html)

> Amazon Redshift Serverless는 현재 AWS 리전의 AWS 계정에 있는 서버리스 환경에 연결됩니다. Amazon Redshift Serverless는 포트 범위 `5431~5455` 및 `8191~8215` 내의 VPC에서 실행됩니다. 기본값은 `5439`입니다. 현재는 API 작업 UpdateWorkgroup 및 AWS CLI 작업 update-workgroup을 통해서만 포트를 변경할 수 있습니다.   

- Port: `5454`

```
aws redshift-serverless update-workgroup --workgroup-name newbank-serverless-workgroup --port 5454
```

## Workgroup Status 확인

```
while true; do 
aws redshift-serverless get-workgroup --workgroup-name newbank-serverless-workgroup --query 'workgroup.status'     
echo `date`; sleep 2; done;
```

## Redshift Serverless Endpoint와 Network interfaces 확인

```
aws ec2 describe-network-interfaces \
--filters "Name=group-id,Values=$(aws ec2 describe-security-groups \
--query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`REDSHIFT_SG`)].GroupId' \
--output text)" \
--query "NetworkInterfaces[*].{InterfaceType: InterfaceType,NetworkInterfaceId: NetworkInterfaceId,Description: Description,PrivateIpAddress: PrivateIpAddress,InstanceOwnerId: Attachment.InstanceOwnerId}" \
--profile default | jq '.[]'
```

---

# Keycloak instance 구성

## Keycloak instance 배포 후 VPC 다이어그램

<img src="images/keycloak-privateroutetable1.png" alt=""></img>

## Keycloak instance 보안 그룹 생성
  
- Group name: `KEYCLOAK_SG`

```
aws ec2 create-security-group --description "KEYCLOAK_SG" --group-name "KEYCLOAK_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```

## Keycloak instance 보안 그룹 Ingress 추가

```
aws ec2 authorize-security-group-ingress \
--group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`KEYCLOAK_SG`)].GroupId' --output text) \
--protocol -1 --port -1 --cidr 10.192.0.0/16 \
--output json | jq '.[]'
```

## Keycloak instance 생성

- Name: `Keycloak`
- AMI: Amazon Linux 2023 AMI
- Instance type: t3.medium
- Key pair : Key pair 선택
- VPC: `newbank`
- Subnet: `newbank Keycloak Private Subnet` 중 선택
    ```
    aws ec2 describe-subnets \
    --filters "Name=tag:Name,Values='newbank Keycloak Private Subnet*'" \
    --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
    ```
- Security group: `KEYCLOAK_SG` 선택
- Advanced details > IAM Instance profile: [Systems Manger로 Keycloak instance에 접속하기 위한 권한 부여](https://repost.aws/knowledge-center/ec2-systems-manager-vpc-endpoints)

## Keycloak instance 정보 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Keycloak'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

## Systems Manger로 Keycloak instance에 접속

```
sudo su -
```

- Java runtime 설치
```
dnf install java-21-amazon-corretto
```

- [Keycloak download](https://www.keycloak.org/downloads)

```
wget https://github.com/keycloak/keycloak/releases/download/24.0.4/keycloak-24.0.4.tar.gz
```

```
tar -zxvf keycloak-24.0.4.tar.gz
```

- nslookup PrivateDnsName

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Keycloak'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

```
nslookup [PrivateDnsName]
```

- https 프로토콜을 사용하기 위해 키와 인증서 생성

```
cd /root/keycloak-24.0.4/bin
```

```
openssl req -newkey rsa:4096 -nodes \
-keyout keycloak-server.key.pem -x509 -days 3650 -out keycloak-server.crt.pem
```

<img src="images/keycloak-self-signed-cert.png" alt=""></img>

## KEYCLOAK_ADMIN와 KEYCLOAK_ADMIN_PASSWORD 정의

```
export KEYCLOAK_ADMIN=admin
export KEYCLOAK_ADMIN_PASSWORD=[Your Keycloak Admin Password]
```

## Https Port `8081`로 Keycloak 시작

```
nohup /root/keycloak-24.0.4/bin/kc.sh start-dev \
--https-port=8081 \
--https-certificate-file=/root/keycloak-24.0.4/bin/keycloak-server.crt.pem \
--https-certificate-key-file=/root/keycloak-24.0.4/bin/keycloak-server.key.pem &
```

```
tail -f nohup.out
```

```
ps -ef | grep keycloak
```

## Keycloak Private Subnets과 연결된 Route Table 변경
> 각 AZ에 있는 newbank Keycloak Private Subnets와 연결된 Route Table을 `newbank PrivateRouteTable1`에서 `newbank PrivateRouteTable2`로 변경

## Keycloak Private Subnets의 Route Table을 `newbank PrivateRouteTable2`으로 변경 후 VPC 다이어그램
<img src="images/keycloak-privateroutetable2.png" alt=""></img>

---

# Windows Gateway instance 구성

## Windows Gateway instance 배포 후 VPC 다이어그램

<img src="images/windows-gateway.png" alt=""></img>

## Windows Gateway instance 보안 그룹 생성

```
aws ec2 create-security-group --description "WINDOWS_GATEWAY_SG" --group-name "WINDOWS_GATEWAY_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```

## Windows Gateway instance 보안 그룹 Ingress 추가
```
aws ec2 authorize-security-group-ingress \
--group-id $(aws ec2 describe-security-groups \
--query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`WINDOWS_GATEWAY_SG`)].GroupId' --output text) \
--protocol tcp \
--port 3389 \
--cidr [Your IPv4 Address]/32 \
--output json | jq '.[]'
```
## Windows Gateway instance 생성
- Name: `Windows Gateway`
- AMI: `Microsoft Windows Server 2022 Base`
- Instance type: `t3.medium`
- Key pair : Key pair 선택
- VPC: `newbank`
- Subnet: `newbank Public Subnet` 중 선택

  ```
  aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values='newbank Public Subnet*'" \
  --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
  ```

- Auto-assign public IP: `Enable`
- Security group: `WINDOWS_GATEWAY_SG`
- Advanced details > IAM Instance profile: SSM Role

## Windows Gateway instance 정보 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Windows Gateway'" \
--query 'Reservations[*].Instances[*].{PublicIpAddress: PublicIpAddress, PublicDnsName: PublicDnsName, PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

---

# DBeaver Windows Client instance 구성
## DBeaver Windows Client instance 배포 후 VPC 다이어그램
<img src="images/windows-dbeaver-privateroutetable1.png" alt=""></img>

## DBeaver Client instance 보안 그룹 생성

```
aws ec2 create-security-group --description "DBEAVER_CLIENT_SG" --group-name "DBEAVER_CLIENT_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```

## DBeaver Client instance 보안 그룹 Ingress 추가

```
aws ec2 authorize-security-group-ingress \
--group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`DBEAVER_CLIENT_SG`)].GroupId' --output text) \
--protocol -1 --port -1 --cidr 10.192.0.0/16 \
--output json | jq '.[]'
```

## DBeaver Client instance 생성
- Name: `DBeaver Windows Client`
- AMI: `Microsoft Windows Server 2022 Base`
- Instance type: `t3.medium`
- Key pair : Key pair 선택
- VPC: `newbank`
- Subnet: `newbank DBeaver Private Subnet` 중 선택

  ```
  aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values='newbank DBeaver Private Subnet*'" \
  --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
  ```

- Auto-assign public IP: `Disable`
- Security group: `DBEAVER_CLIENT_SG`
- Advanced details > IAM Instance profile: SSM Role

## DBeaver Client instance 정보 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='DBeaver Windows Client'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

---

# DBeaver Windows Client instance에 접속

## Instances 및 Redshift Serverless Workgroup Endpoint 접속 정보 조회
- Windows Gateway instance PublicIpAddress 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Windows Gateway'" \
--query 'Reservations[*].Instances[*].{PublicIpAddress: PublicIpAddress, PublicDnsName: PublicDnsName}' | jq '.[]'
```

- DBeaver Windows Client PrivateIpAddress 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='DBeaver Windows Client'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

- Keycloak instance PrivateIpAddress 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Keycloak'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

- Redshift Serverless Workgroup(`newbank-serverless-workgroup`) Endpoint 조회

```
aws redshift-serverless get-workgroup --workgroup-name newbank-serverless-workgroup --query 'workgroup.endpoint.{address: address, port: port}' --output json
```


## Windows Gateway을 통해 `DBeaver Windows Client instance` 접속

<img src="images/connect-dbeaver-windows-client-instance-1.png" alt=""></img>


## `DBeaver Windows Client`에 tools 설치
- Server Manager > Local Server > IE Enhanced Security Configuration: Off
- ~~Chrome 설치~~
- ~~Chrome을 기본 브라우저로 설정 및 시크릿 모드 실행~~
- ~~크롬 확장 프로그램 SAML-tracer 설치 및 실행~~
- Firefox 설치 및 기본 브라우저로 설정
- Firefox 확장 프로그램 SAML-tracer 설치 및 실행
- [DBeaver 다운로드](https://dbeaver.io/download/)
- DBeaver 설치
- [Redshift JDBC driver 다운로드](https://s3.amazonaws.com/redshift-downloads/drivers/jdbc/2.1.0.28/redshift-jdbc42-2.1.0.28.zip)
- Redshift JDBC driver 압축 풀기

## Redshift Serverless Workgroup(`newbank-serverless-workgroup`) Endpoint 연결성 확인

- nslookup [Redshift Serverless Endpoint]

```
nslookup newbank-serverless-workgroup.account-id.ap-northeast-2.redshift-serverless.amazonaws.com
```

- Test-NetConnection [Redshift Serverless Endpoint] -Port 5454

```
Test-NetConnection newbank-serverless-workgroup.account-id.ap-northeast-2.redshift-serverless.amazonaws.com -Port 5454
```

## Keycloak Admin Console 접속
- Keycloak instance PrivateIpAddress 조회

```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Keycloak'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```

## Keycloak Admin Console 접속

```
https://[Keycloak PrivateDnsName]:8081
```

<img src="images/keycloak-admin-site-8081.png" alt=""></img>
<img src="images/keycloak-admin-site-signin.png" alt=""></img>
<img src="images/keycloak-admin-site-welcome-mater-realm.png" alt=""></img>

## Realm 신규 생성

- Realm name: `newbankrealm`

<img src="images/keycloak-create-realm.png" alt=""></img>
<img src="images/keycloak-create-realm-newbankrealm.png" alt=""></img>
<img src="images/keycloak-welcome-to-newbankrealm.png" alt=""></img>

- 즐겨찾기 추가

## DBeaver에 Redshift JDBC driver Connection Template(`jdbc:redshift://`) 등록

- DBeaver > Database > Driver Manager > New
- Libraries
  - Add Folder > redshift-jdbc42-2.1.0.28
- Settings
  - Driver Name: `Redshift-Serverless-jdbc`
  - Driver Type: `PostgreSQL`
  - Class Name: `com.amazon.redshift.jdbc42.Driver`
  - URL Template: `jdbc:redshift://{host}:{port}/{database}`
  - Default Port: `5454`
  - Default Database: `dev`   

<img src="images/dbeaver-redshift-serverless-jdbc.png" alt=""></img>

- OK

## DBeaver에 Redshift JDBC driver Connection Template(`jdbc:redshift:iam://`) 등록
- DBeaver > Database > Driver Manager > 앞서 등록한 Driver(`Redshift-Serverless-jdbc`) Copy
- Settings
  - Driver Name: `Redshift-Serverless-iam`
  - Driver Type: `PostgreSQL`
  - Class Name: `com.amazon.redshift.jdbc42.Driver`
  - URL Template: `jdbc:redshift:iam://{host}:{port}/{database}`
  - Default Port: `5454`
  - Default Database: `dev`

<img src="images/dbeaver-redshift-serverless-iam.png" alt=""></img>

- OK

---

# newbankrealm SAML 2.0 Identity Provider Metadata 다운로드

## Keycloak Admin Console에서 newbankrealm 접속

```
https://[Keycloak PrivateDnsName]:8081/admin/master/console/#/newbankrealm
```

## Keycloak Admin Console self-signed 인증서 다운로드

<img src="images/keycloak-newbankrealm-saml-download1.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-download2.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-download3.png" alt=""></img>

## self-signed 인증서 Trusted Root Certification Authorities 등록

<img src="images/keycloak-newbankrealm-saml-cert1.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-cert2.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-cert3.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-cert4.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-cert5.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-cert6.png" alt=""></img>

## newbankrealm > Realm settings

<img src="images/keycloak-newbankrealm-saml-metadata1.png" alt=""></img>
<img src="images/keycloak-newbankrealm-saml-metadata2.png" alt=""></img>

## newbankrealm SAML 2.0 Identity Provider Metadata URL 복사

<img src="images/keycloak-newbankrealm-saml-metadata3.png" alt=""></img>

## Metadata 다운로드

```
curl https://[Keycloak PrivateDnsName]:8081/realms/newbankrealm/protocol/saml/descriptor -OutFile descriptor.xml
```

---

# AWS IAM Identity provider 추가

## IAM > Identity providers

<img src="images/aws-iam-identity-provider1.png" alt=""></img>

## Add Provider

## Provider name: `newbankrealm`

## Metadata document: 앞서 Keycloak newbankrealm에서 다운로드한 `descriptor.xml` 선택

<img src="images/aws-iam-identity-provider2.png" alt=""></img>

## Add Provider

## newbankrealm saml provider arn 조회

```
aws iam list-saml-providers
```

Output
```
{
    "SAMLProviderList": [
        {
            "Arn": "arn:aws:iam::account-id:saml-provider/newbankrealm",
            "ValidUntil": "2124-06-14T03:13:34+00:00",
            "CreateDate": "2024-06-14T03:13:34+00:00"
        }
    ]
}
```

---

# AWS IAM Role 추가

## IAM > Roles > Create role

- Trusted entity type: `SAML 2.0 federation`

- SAML 2.0–based provider: `newbankrealm`

- Access to be allowed: `Allow programmatic access only`

- Attribute: `SAML:aud`

- Value: `http://localhost:7890/redshift/`

<img src="images/aws-iam-role1.png" alt=""></img>

- Next

- Add permissions: `AmazonRedshiftFullAccess` 선택

- Next

- Role name: `newbankrealm_redshift_admin`

- Create role


## newbankrealm_redshift_admin role 조회

```
aws iam get-role --role-name newbankrealm_redshift_admin
```

Output
```
{
    "Role": {
        "Path": "/",
        "RoleName": "newbankrealm_redshift_admin",
        "RoleId": "AROA2ADNFLLFDAQ22RNRO",
        "Arn": "arn:aws:iam::account-id:role/newbankrealm_redshift_admin",
        "CreateDate": "2024-06-14T03:19:09+00:00",
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": "arn:aws:iam::account-id:saml-provider/newbankrealm"
                    },
                    "Action": "sts:AssumeRoleWithSAML",
                    "Condition": {
                        "StringEquals": {
                            "SAML:aud": "http://localhost:7890/redshift/"
                        }
                    }
                }
            ]
        },
        "Description": "",
        "MaxSessionDuration": 3600,
        "RoleLastUsed": {}
    }
}
```

---

# Keycloak newbankrealm User 생성

## Keycloak Admin Console에서 newbankrealm 접속

```
https://[Keycloak PrivateDnsName]:8081/admin/master/console/#/newbankrealm
```

<img src="images/keycloak-add-user1.png" alt=""></img>

## 사용자 생성

<img src="images/keycloak-add-user2.png" alt=""></img>
<img src="images/keycloak-add-user3.png" alt=""></img>
<img src="images/keycloak-add-user4.png" alt=""></img>
<img src="images/keycloak-add-user5.png" alt=""></img>

## 사용자 접속 확인

- Clients > Client ID(`account`) > Home URL Click(or Copy)

<img src="images/keycloak-add-user6.png" alt=""></img>
<img src="images/keycloak-add-user7.png" alt=""></img>
<img src="images/keycloak-add-user8.png" alt=""></img>
<img src="images/keycloak-add-user9.png" alt=""></img>
<img src="images/keycloak-add-user10.png" alt=""></img>

---

# Keycloak newbankrealm Client 구성

## DBeaver Windows Client instance에서 AWS signin saml-metadata 다운로드

```
curl https://signin.aws.amazon.com/static/saml-metadata.xml -OutFile saml-metadata.xml
```

## Keycloak Admin Console에서 newbankrealm 접속

```
https://[Keycloak PrivateDnsName]:8081/admin/master/console/#/newbankrealm
```

<img src="images/keycloak-newbankrealm-add-client1.png" alt=""></img>

## Import Client(`urn:amazon:webservices`)

<img src="images/keycloak-newbankrealm-add-client2.png" alt=""></img>
<img src="images/keycloak-newbankrealm-add-client3.png" alt=""></img>
<img src="images/keycloak-newbankrealm-add-client4.png" alt=""></img>
<img src="images/keycloak-newbankrealm-add-client5.png" alt="SAVE"></img>

## Client(`urn:amazon:webservices`) Access settings

- Home URL: `/realms/newbankrealm/protocol/saml/clients/signin`
- Valid redirect URIs: `http://localhost:7890/redshift/`
- IDP-Initiated SSO URL name: `signin`
- Save

<img src="images/keycloak-newbankrealm-add-client6.png" alt=""></img>

## Client(`urn:amazon:webservices`) Advanced

- Assertion Consumer Service POST Binding URL: `http://localhost:7890/redshift/`

<img src="images/keycloak-newbankrealm-add-client7.png" alt=""></img>
<img src="images/keycloak-newbankrealm-add-client8.png" alt="SAVE"></img>

---

# DBeaver Test Connection as a redshift admin user

## Redshift Serverless Endpoint 정보

```
aws redshift-serverless get-workgroup --workgroup-name newbank-serverless-workgroup --query 'workgroup.endpoint.{address: address, port: port}' --output json
```

Output
```
{
    "address": "newbank-serverless-workgroup.account-id.ap-northeast-2.redshift-serverless.amazonaws.com",
    "port": 5454
}
```

## 새로운 connection 생성

<img src="images/dbeaver-jdbc1.png" alt=""></img>

## 데이터베이스, 커넥션 템플릿 선택

- Name: `Redshift-Serverless-jdbc`

<img src="images/dbeaver-jdbc2.png" alt=""></img>

- DB 연결 설정
- Host: `[Redshift Serverless Endpoint address]`
- Port: `[Redshift Serverless Endpoint port]`
- Database: `dev`
- Username: `[Redshift Admin user name]`
- Password: `[Redshift Admin user password]`

<img src="images/dbeaver-jdbc3.png" alt=""></img>

## Test Connection

<img src="images/dbeaver-jdbc4.png" alt=""></img>

## Connection 생성

- Connection Name: `dev-jdbc`

<img src="images/dbeaver-jdbc5.png" alt=""></img>

---

# DBeaver Test Connection using SAML 2.0

## 새로운 connection 생성

<img src="images/dbeaver-iam1.png" alt=""></img>

## 데이터베이스, 커넥션 템플릿 선택

- Name: `Redshift-Serverless-iam`

<img src="images/dbeaver-iam2.png" alt=""></img>

- DB 연결 설정
- Host: `[Redshift Serverless Endpoint address]`
- Port: `5454`
- Database: `dev`

<img src="images/dbeaver-iam3.png" alt=""></img>

- SSL 활성화

<img src="images/dbeaver-iam4.png" alt=""></img>

- Keycloak login url property 추가

  - Driver Properties > Add user property > Property Name: `login_url`

<img src="images/dbeaver-iam5.png" alt=""></img>
<img src="images/dbeaver-iam6.png" alt=""></img>

  - Client ID(`urn:amazon:webservices`) Home URL 복사 > `login_url`의 Value 입력
  - Value: `https://[Keycloak PrivateDnsName]:8081/realms/newbankrealm/protocol/saml/clients/signin`

<img src="images/dbeaver-iam7.png" alt=""></img>
<img src="images/dbeaver-iam8.png" alt=""></img>

- Redshift JDBC plug-in property 추가

  - Driver Properties > Add user property > Property Name: `plugin_name`
  - Value: `com.amazon.redshift.plugin.BrowserSamlCredentialsProvider`

<img src="images/dbeaver-iam9.png" alt=""></img>
<img src="images/dbeaver-iam10.png" alt=""></img>

## Test Connection

- Click Test Connection

<img src="images/dbeaver-iam11.png" alt=""></img>

- Test Connection 시작

<img src="images/dbeaver-iam12.png" alt=""></img>

- User property(`login_url`)에 설정한 Keycloak login 페이지가 정상적으로 열려야 합니다.
- Username, Password 입력 후 Sign in

<img src="images/dbeaver-iam13.png" alt=""></img>

- Authentication Redirect

<img src="images/dbeaver-iam14.png" alt=""></img>

- Keycloak login 성공 시 출력되는 화면입니다.

<img src="images/dbeaver-iam15.png" alt=""></img>

- Connection error

> 아직 newbankrealm에 Role을 구성하지 않았기 때문에 아래 error(`No role found in SamlAssertion`)는 정상적입니다.

```
Connection error

No role found in SamlAssertion:     PHNhbWxwOlJlc3Bv...
```

<img src="images/dbeaver-iam16.png" alt=""></img>

- Port 7890 확인
```
netstat -ano | findstr 7890
```

<img src="images/dbeaver-iam22-7890.png" alt=""></img>

- SAML-tracer 확인

<img src="images/dbeaver-iam18.png" alt=""></img>
<img src="images/dbeaver-iam19.png" alt=""></img>

- Keycloak > newbankrealm > Sessions 확인

<img src="images/dbeaver-iam17.png" alt=""></img>

- Connection 생성

  - Connectio name: `dev-iam`

<img src="images/dbeaver-iam20.png" alt=""></img>
<img src="images/dbeaver-iam21.png" alt=""></img>

---

# Keycloak newbankrealm Mapper(SAML Attribute) 구성

## Keycloak newbankrealm admin 접속

<img src="images/keycloak-role1.png" alt=""></img>

## Client ID(`urn:amazon:webservices`) 선택

<img src="images/keycloak-role2.png" alt=""></img>

## Client scopes > role_list 삭제

<img src="images/keycloak-role3.png" alt=""></img>
<img src="images/keycloak-role4.png" alt=""></img>
<img src="images/keycloak-role5.png" alt=""></img>
<img src="images/keycloak-role6.png" alt=""></img>

## Client scopes > `urn:amazon:webservices-dedicated` > Scope 변경

- Full scope allowed: `Off`

<img src="images/keycloak-role7.png" alt=""></img>

## Clients > Client ID(urn:amazon:webservices) > Roles

- Create role

<img src="images/keycloak-role12.png" alt=""></img>

- Role name: `Redshift Admin`

<img src="images/keycloak-role13.png" alt=""></img>
<img src="images/keycloak-role14.png" alt=""></img>

## Client scopes > `urn:amazon:webservices-dedicated` > Mappers

- 자동으로 등록된 Mappers 삭제

```
https://aws.amazon.com/SAML/Attributes/Role
```
```
https://aws.amazon.com/SAML/Attributes/RoleSessionName
```

<img src="images/keycloak-role8.png" alt=""></img>
<img src="images/keycloak-role9.png" alt=""></img>

## Add mapper (By configuration)

- Mapper type: `Role list`
- Name: `Role`
- Role attribute name

  ```
  https://aws.amazon.com/SAML/Attributes/Role
  ```

- Friendly name: `Role`

<img src="images/keycloak-role10.png" alt=""></img>

## Add mapper (By configuration)

- Mapper type: `User Property`
- Name: `RoleSessionName`
- Property: `email`
- Friendly Name: `RoleSessionName`
- SAML Attribute Name

  ```
  https://aws.amazon.com/SAML/Attributes/RoleSessionName
  ```

<img src="images/keycloak-role11.png" alt=""></img>

## Add mapper (By configuration)

- Mapper type: `Role Name Mapper`
- Name: `Redshift Admin Role Mapping`
- Role: `urn:amazon:webservices Redshift Admin` 선택
- New Role Name: [role arn],[identity provider arn]

  ```
  arn:aws:iam::account-id:role/newbankrealm_redshift_admin,arn:aws:iam::account-id:saml-provider/newbankrealm
  ```

<img src="images/keycloak-role15.png" alt=""></img>

---

# Keycloak Group, Member, Role mapping 구성

## Create Group

- Name: `Redshift Admin Group`

<img src="images/keycloak-role-group1.png" alt=""></img>

## Add members

<img src="images/keycloak-role-group2.png" alt=""></img>
<img src="images/keycloak-role-group3.png" alt=""></img>
<img src="images/keycloak-role-group4.png" alt=""></img>
<img src="images/keycloak-role-group5.png" alt=""></img>

## Group Role mapping

<img src="images/keycloak-role-group7.png" alt=""></img>
<img src="images/keycloak-role-group8.png" alt=""></img>

---

# DBeaver Test Connection

## 사전 점검

- Keycloak neewbankrealm Sessions

<img src="images/dbeaver-iam-privateroutetable1.png" alt=""></img>

## netstat

```
netstat -ano | findstr 7890
```

<img src="images/dbeaver-iam-privateroutetable2.png" alt=""></img>

## Connection 선택: `dev-iam`

<img src="images/dbeaver-iam-privateroutetable3.png" alt=""></img>

## Test Connection

<img src="images/dbeaver-iam-privateroutetable4.png" alt=""></img>

## Keycloak login page

<img src="images/dbeaver-iam-privateroutetable5.png" alt=""></img>

## Username, Password 입력 후 Sign in

<img src="images/dbeaver-iam-privateroutetable6.png" alt=""></img>

## Authentication Redirect

<img src="images/dbeaver-iam-privateroutetable7.png" alt=""></img>

## Keycloak login 성공 시 출력되는 화면입니다.

<img src="images/dbeaver-iam-privateroutetable8.png" alt=""></img>

## Connected

<img src="images/dbeaver-iam-privateroutetable9.png" alt=""></img>

## Port 7890 확인

<img src="images/dbeaver-iam22-7890.png" alt=""></img>

## SAML-tracer 확인

<img src="images/dbeaver-iam-privateroutetable10.png" alt=""></img>
<img src="images/dbeaver-iam-privateroutetable11.png" alt=""></img>

## Keycloak session 확인

<img src="images/dbeaver-iam-privateroutetable12.png" alt=""></img>

## Query

<img src="images/dbeaver-iam-privateroutetable13.png" alt=""></img>


# DBeaver Private Subnet의 Route Table 변경
PrivateRouteTable1 --> PrivateRouteTable2
<br>
<img src="images/windows-dbeaver-privateroutetable2.png" alt=""></img>
</br>

# DBeaver Private Subnet의 Route Table 변경
PrivateRouteTable2 --> PrivateRouteTable3
<br>
<img src="images/windows-dbeaver-privateroutetable3.png" alt=""></img>
</br>

---
