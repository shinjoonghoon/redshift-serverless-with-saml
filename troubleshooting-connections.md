# [Amazon Redshift 연결 문제 해결](https://docs.aws.amazon.com/redshift/latest/mgmt/troubleshooting-connections.html)

## Windows netstat

```
netstat -ano | findstr 7890
```

```
taskkill /F /PID
```

## Change TCP/IP timeout settings

https://docs.aws.amazon.com/redshift/latest/mgmt/connecting-firewall-guidance.html

Windows — If your client runs on Windows, edit the values for the following registry settings under HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\:

KeepAliveTime: 30000

KeepAliveInterval: 1000

TcpMaxDataRetransmissions: 10

These settings use the DWORD data type. If they do not exist under the registry path, you can create the settings and specify these recommended values. For more information about editing the Windows registry, refer to Windows documentation.

After you set these values, restart your computer for the changes to take effect.


## TCP/IP Configuration Parameters
https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2003/cc739819(v=ws.10)?redirectedfrom=MSDN

```
reg add HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters /v KeepAliveTime /t REG_DWORD /d 30000 /f
```
```
reg add HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters /v KeepAliveInterval /t REG_DWORD /d 1000 /f
```
```
reg add HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters /v TcpMaxDataRetransmissions /t REG_DWORD /d 10 /f
```
```
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "KeepAliveTime"
```
```
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "KeepAliveInterval"
```
```
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "TcpMaxDataRetransmissions"
```

---
