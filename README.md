# redshift-serverless-with-saml


# VPC 구성
* VPC 정보 조회
* 서브넷 정보 조회

# VPC Endpoints 구성
* VPC Endpoints 보안 그룹 생성
* VPC Endpoints 보안 그룹 Ingress 추가
* VPC Endpoints 서브넷 조회
* VPC Endpoints 생성
* VPC Endpoints 조회
* Network Insterface 조회

# Redshift Serverless 구성
* Redshift Serverless 보안 그룹 생성
* Redshift Serverless 보안 그룹 Ingress 추가
* Redshift Serverless 생성
* Port 변경
* Redshift Serverless Endpoint 확인
* Network Interfaces 확인

# Keycloak instance 구성
* Keycloak instance 보안 그룹 생성
* Keycloak instance 보안 그룹 Ingress 추가
* Keycloak instance 생성
* Keycloak instance 정보 조회
* Keycloak instance 접속
* Java runtime 설치
* Keycloak download
* nslookup PrivateDnsName
* https 프로토콜을 사용하기 위해 키와 인증서 생성
* 8081 Port로 Keycloak 시작
* Keycloak Private Subnet의 Route Table 변경

# Windows Gateway instance 구성
* Windows Gateway instance 보안 그룹 생성
* Windows Gateway instance 보안 그룹 Ingress 추가
* Windows Gateway instance 생성

# DBeaver Windows Client instance 구성
* DBeaver Client instance 보안 그룹 생성
* DBeaver Client instance 보안 그룹 Ingress 추가
* DBeaver Client instance 생성

# DBeaver Windows Client instance에 접속
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

# DBeaver Private Subnet의 Route Table 변경
PrivateRouteTable2 --> PrivateRouteTable3

# CloudTrail

# CloudWatch Logs

# VPC Flow Logs


