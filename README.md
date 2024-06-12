# redshift-serverless-with-saml
> Redshift Serverless, SAML, Keycloak, DBeaver

# VPC 구성
* 다운로드 [YAML](https://github.com/shinjoonghoon/redshift-serverless-with-saml/blob/main/redshift-serverless-with-saml.yaml).
  - Stack name: `newbank`
  - EnvironmentName: `newbank`
* yaml 배포 후 VPC 다이어그램
<img src="images/vpc-cf.png" alt=""></img>
* 환경 변수 정의
```
VPC_ID=
REGION=$(aws configure get region)
echo $VPC_ID
echo $REGION
```
* VPC 정보 조회
```
aws ec2 describe-vpcs --vpc-ids $VPC_ID
```
* 서브넷 정보 조회
```
aws ec2 describe-subnets --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
```
* [VPC Flow Logs 조회 환경 구성](https://docs.aws.amazon.com/ko_kr/athena/latest/ug/vpc-flow-logs.html)

# VPC Endpoints 구성
* VPC Endpoints 적용 후 VPC 다이어그램
<img src="images/vpc-endpoints.png" alt=""></img>

* VPC Endpoints 보안 그룹 생성
```
aws ec2 create-security-group --description "VPC_ENDPOINT_SG" --group-name "VPC_ENDPOINT_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```
* VPC Endpoints 보안 그룹 Ingress 추가
```
aws ec2 authorize-security-group-ingress \
    --group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`VPC_ENDPOINT_SG`)].GroupId' --output text) \
    --protocol -1 --port -1 --cidr 10.192.0.0/16 \
    \
    --output json | jq '.[]'
```
* VPC Endpoints 서브넷 조회
```
aws ec2 describe-subnets \
--filters "Name=tag:Name,Values='newbank VPC Endpoints Private Subnet*'" \
--query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' \
--output text
```
* VPC Endpoints 생성
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
    --service-name  $v \
    \
    --output json | jq '.[]'
done
```
```
aws ec2 create-vpc-endpoint \
    --region $REGION  \
    --vpc-endpoint-type Gateway \
    --vpc-id  $VPC_ID \
    --route-table-ids $(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --region ap-northeast-2 --query 'RouteTables[].RouteTableId' --output text) \
    --service-name com.amazonaws.$REGION.s3 \
    \
    --output json | jq '.[]'
```
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
    \
    --output json | jq '.[]'
```
* VPC Endpoints 조회
```
while true; do 
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" --region $REGION  --query 'VpcEndpoints[].[State,VpcEndpointType,ServiceName]' --output text;
echo `date`; sleep 2; done;
```
* Network Insterface 조회
```
aws ec2 describe-network-interfaces --filters "Name=interface-type,Values=vpc_endpoint" "Name=vpc-id,Values=$VPC_ID" \
--query 'NetworkInterfaces[*].{NetworkInterfaceId:NetworkInterfaceId,PrivateIpAddress:PrivateIpAddress, GroupName:Groups[0].GroupName}' --output text
```

# Redshift Serverless 구성

* [Availability Zone IDs](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-usage-considerations.html)
When you configure your Amazon Redshift Serverless instance, open Additional considerations, and make sure that the subnet IDs provided in Subnet contain at least three of the supported Availability Zone IDs.

* Redshift Serverless 배포 후 VPC 다이어그램
<img src="images/redshift-serverless-1.png" alt=""></img>

* Redshift Serverless 보안 그룹 생성
```
aws ec2 create-security-group --description "REDSHIFT_SG" --group-name "REDSHIFT_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```
* Redshift Serverless 보안 그룹 Ingress 추가
```
aws ec2 authorize-security-group-ingress \
    --group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`REDSHIFT_SG`)].GroupId' --output text) \
    --protocol -1 --port -1 --cidr 10.192.0.0/16 \
    \
    --output json | jq '.[]'
```
* Redshift Serverless 생성
  - Workgroup name:  `newbank-serverless-workgroup`
  - Base capacity: `32`
  - Virtual private cloud (VPC): `newbank`
  - VPC security groups:
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
  - Admin password: Manually add the admin password(secretsmanager 사용 고려)
  - Permissions > Associated IAM roles (0) --> No resoureces
  - Security and encryption > Export these logs > User log, Connection log, User activity log
  - Next
  - Review and create
  - Create


* Redshift Serverless 상태 확인
  - Workgroup Status 확인
  ```
      while true; do 
  aws redshift-serverless get-workgroup --workgroup-name newbank-serverless-workgroup --query 'workgroup.status'     
  echo `date`; sleep 2; done;
  ```
  - Namespace Status 확인
  ```
  while true; do 
  aws redshift-serverless get-namespace --namespace-name newbank-serverless-namespace --query 'namespace.status'     
  echo `date`; sleep 2; done;
  ```
* Port 변경
```
aws redshift-serverless update-workgroup --workgroup-name newbank-serverless-workgroup --port 5454
```
* Redshift Serverless Endpoint와 Network interfaces 확인
```
aws ec2 describe-network-interfaces \
--filters "Name=group-id,Values=$(aws ec2 describe-security-groups \
--query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`REDSHIFT_SG`)].GroupId' \
--output text)" \
--query "NetworkInterfaces[*].{InterfaceType: InterfaceType,NetworkInterfaceId: NetworkInterfaceId,Description: Description,PrivateIpAddress: PrivateIpAddress,InstanceOwnerId: Attachment.InstanceOwnerId}" \
--profile default | jq '.[]'
```


# Keycloak instance 구성
* Keycloak instance 배포 후 VPC 다이어그램
<img src="images/keycloak-privateroutetable1.png" alt=""></img>

* Keycloak instance 보안 그룹 생성
```
aws ec2 create-security-group --description "KEYCLOAK_SG" --group-name "KEYCLOAK_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```
* Keycloak instance 보안 그룹 Ingress 추가
```
aws ec2 authorize-security-group-ingress \
    --group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`KEYCLOAK_SG`)].GroupId' --output text) \
    --protocol -1 --port -1 --cidr 10.192.0.0/16 \
    --output json | jq '.[]'
```
* Keycloak instance 생성
  - Name: `Keycloak`
  - AMI: Amazon Linux 2023 AMI
  - Instance type: t3.medium
  - Key pair : Key pair 선택
  - VPC: `newbank`
  - Subnet: newbank Keycloak Private Subnet 중 선택
  ```
  aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values='newbank Keycloak Private Subnet*'" \
  --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
  ```
  - Security group: `KEYCLOAK_SG`
  - Advanced details > IAM Instance profile: [Systems Manger로 Keycloak instance에 접속하기 위한 권한 부여](https://repost.aws/knowledge-center/ec2-systems-manager-vpc-endpoints)

* Keycloak instance 정보 조회
```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Keycloak'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```
* Systems Manger로 Keycloak instance에 접속
```
sudo su -
```
* Java runtime 설치
```
dnf install java-21-amazon-corretto
```
* [Keycloak download](https://www.keycloak.org/downloads)
```
wget https://github.com/keycloak/keycloak/releases/download/24.0.4/keycloak-24.0.4.tar.gz
```
```
tar -zxvf keycloak-24.0.4.tar.gz
```
* nslookup PrivateDnsName
```
aws ec2 describe-instances \
--filters "Name=tag:Name,Values='Keycloak'" \
--query 'Reservations[*].Instances[*].{PrivateIpAddress: PrivateIpAddress, PrivateDnsName: PrivateDnsName}' | jq '.[]'
```
```
nslookup [PrivateDnsName]
```
* https 프로토콜을 사용하기 위해 키와 인증서 생성
```
cd /root/keycloak-24.0.4/bin
```
```
openssl req -newkey rsa:4096 -nodes \
-keyout keycloak-server.key.pem -x509 -days 3650 -out keycloak-server.crt.pem
```
<br>
<img src="images/keycloak-self-signed-cert.png" alt=""></img>
</br>

* KEYCLOAK_ADMIN와 KEYCLOAK_ADMIN_PASSWORD 정의
```
export KEYCLOAK_ADMIN=admin
export KEYCLOAK_ADMIN_PASSWORD=[Your Keycloak Admin Password]
```

* 8081 Port로 Keycloak 시작
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
* Keycloak Private Subnet의 Route Table 변경: 각 AZ에 있는 newbank Keycloak Private Subnet와 연결된 Route Table을 `newbank PrivateRouteTable1`에서 `newbank PrivateRouteTable2`로 변경

* Keycloak Private Subnet의 Route Table 변경 후 VPC 다이어그램
<img src="images/keycloak-privateroutetable2.png" alt=""></img>

# Windows Gateway instance 구성
* Windows Gateway instance 배포 후 VPC 다이어그램
<img src="images/windows-gateway.png" alt=""></img>

* Windows Gateway instance 보안 그룹 생성
```
aws ec2 create-security-group --description "WINDOWS_GATEWAY_SG" --group-name "WINDOWS_GATEWAY_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```
* Windows Gateway instance 보안 그룹 Ingress 추가
```
aws ec2 authorize-security-group-ingress \
    --group-id $(aws ec2 describe-security-groups \
    --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`WINDOWS_GATEWAY_SG`)].GroupId' --output text) \
    --protocol tcp \
    --port 3389 \
    --cidr [Your IPv4 Address]/32 \
    --output json | jq '.[]'
```
* Windows Gateway instance 생성
  - Name: `Windows Gateway`
  - AMI: Microsoft Windows Server 2022 Base
  - Instance type: t3.medium
  - Key pair : Key pair 선택
  - VPC: `newbank`
  - Subnet: newbank Public Subnet 중 선택
  ```
  aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values='newbank Public Subnet*'" \
  --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
  ```
  - Auto-assign public IP: `Enable`
  - Security group: `WINDOWS_GATEWAY_SG`
  - Advanced details > IAM Instance profile: SSM Role
 
# DBeaver Windows Client instance 구성
* DBeaver Windows Client instance 배포 후 VPC 다이어그램
<img src="images/windows-dbeaver-privateroutetable1.png" alt=""></img>

* DBeaver Client instance 보안 그룹 생성
```
aws ec2 create-security-group --description "DBEAVER_CLIENT_SG" --group-name "DBEAVER_CLIENT_SG" --vpc-id $VPC_ID --output json | jq '.[]'
```
* DBeaver Client instance 보안 그룹 Ingress 추가
```
aws ec2 authorize-security-group-ingress \
    --group-id $(aws ec2 describe-security-groups --query 'SecurityGroups[?(VpcId==`'$VPC_ID'` && GroupName==`DBEAVER_CLIENT_SG`)].GroupId' --output text) \
    --protocol -1 --port -1 --cidr 10.192.0.0/16 \
    --output json | jq '.[]'
```
* DBeaver Client instance 생성
  - Name: `DBeaver Windows Client`
  - AMI: Microsoft Windows Server 2022 Base
  - Instance type: t3.medium
  - Key pair : Key pair 선택
  - VPC: `newbank`
  - Subnet: newbank DBeaver Private Subnet 중 선택
  ```
  aws ec2 describe-subnets \
  --filters "Name=tag:Name,Values='newbank DBeaver Private Subnet*'" \
  --query 'sort_by(Subnets, &CidrBlock)[?(VpcId==`'$VPC_ID'`)].{CidrBlock: CidrBlock, SubnetId: SubnetId, Tags: Tags[?Key == `Name`].Value | [0]}' --output text
  ```
  - Auto-assign public IP: `Disable`
  - Security group: `DBEAVER_CLIENT_SG`
  - Advanced details > IAM Instance profile: SSM Role

# DBeaver Windows Client instance에 접속
* Windows Gateway을 통해 DBeaver Windows Client instance 접속
<img src="images/connect-dbeaver-windows-client-instance.png" alt=""></img>
  - Instances 정보 조회
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
* Keycloak admin 접속 확인
* DBeaver 설치
* Redshift Serverless Endpoint 연결성 확인
  - Test-NetConnection
* Redshift JDBC driver 다운로드
* 새로운 드라이버 생성
* 새로운 Connection 생성
  - Admin user
* CloudWatch logs 확인

# Keycloak 새로운 Realm과 사용자 생성
* Realm 생성
* 사용자 생성
* 사용자 접속 확인

# AWS IAM Identity provider 구성
* SAML 2.0 Identity Provider Metadata 다운로드
* IAM Console 접속
* Add Provider
* saml provider arn 확인

# AWS IAM Role 추가
* role arn 확인

# Keycloak Client 구성
* AWS signin saml-metadata 다운로드
* Keycloak admin 접속
* Import Client
* Client Access settings

# DBeaver Test Connection
* 새로운 connection 생성
* login_url
* plugin_name
* Connection error
* SAML-tracer 확인
* Connection 생성
* Keycloak session 확인

# Keycolak Mapper(SAML Attribute) 구성
* Keycloak admin 접속
* Role
* RoleSessionName
* Role Name Mapper 구성

# Keycloak Group 생성

# Test Connection

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

# CloudTrail

# CloudWatch Logs

# VPC Flow Logs

# IP 기반 접근 제어

# Redshift provisioned cluster



