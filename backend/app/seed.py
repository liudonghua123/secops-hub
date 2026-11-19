"""Seed data: realistic demo dataset for a unit-level security team."""
import os
import random

from .database import Base, SessionLocal, engine
from .models import Asset, Finding, IntelItem, ScanTask, User, Vulnerability
from .auth import hash_password

DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@2026")

ASSETS = [
    ("单位门户网站", "domain", "www.example.gov.cn", "信息中心", "高", "京ICP备2026000001号", True, "Nginx,Java,若依"),
    ("OA 办公系统", "domain", "oa.example.gov.cn", "办公室", "高", "京ICP备2026000001号", True, "Apache,Tomcat,泛微OA"),
    ("邮件系统", "domain", "mail.example.gov.cn", "信息中心", "高", "", True, "Coremail"),
    ("业务申报系统", "domain", "sb.example.gov.cn", "业务一处", "高", "京ICP备2026000002号", True, "Java,Spring,MySQL"),
    ("数据交换平台", "host", "10.1.10.21", "信息中心", "高", "", False, "CentOS,Oracle"),
    ("文件服务器", "host", "10.1.10.30", "信息中心", "中", "", False, "Windows Server,SMB"),
    ("内部知识库", "domain", "wiki.example.gov.cn", "综合处", "中", "", False, "Confluence"),
    ("视频会议系统", "app", "会议通App", "办公室", "中", "京ICP备2026000003号", True, "Android,iOS"),
    ("微信公众号服务", "app", "单位微信公众号", "宣传处", "低", "", True, "微信小程序"),
    (" VPN 网关", "host", "60.10.2.15", "信息中心", "高", "", True, "深信服VPN"),
    ("备份系统", "host", "10.1.10.40", "信息中心", "高", "", False, "Linux,Veritas"),
    ("人事管理系统", "domain", "hr.example.gov.cn", "人事处", "中", "", False, "PHP,ThinkPHP"),
    ("资产管理小程序", "app", "资产通小程序", "财务处", "低", "", True, "微信小程序"),
    ("安全监测平台", "host", "10.1.10.50", "信息中心", "高", "", False, "Linux,ES"),
    ("打印机管理服务", "host", "10.1.20.11", "行政处", "低", "", False, "HP Print"),
]

VULNS = [
    ("CVE-2021-44228", "CNNVD-2021-49", "", "Apache Log4j2 远程代码执行漏洞（Log4Shell）", "严重", 10.0, "NVD", "Apache Log4j2 的 JNDI Lookup 功能存在远程代码执行漏洞，攻击者可通过构造特殊请求在目标服务器执行任意代码。", "log4j,java", True, True, "升级 Log4j2 至 2.17+，临时方案：设置 log4j2.formatMsgNoLookups=true。", "2021-12-10"),
    ("CVE-2023-34362", "CNNVD-2023-36", "", "MOVEit Transfer SQL 注入漏洞", "严重", 9.8, "NVD", "MOVEit Transfer 存在未认证 SQL 注入漏洞，可导致未授权访问及数据泄露，已被 Cl0p 勒索组织大规模利用。", "moveit", True, True, "升级至最新版本，检查是否已被入侵。", "2023-06-02"),
    ("CVE-2024-3400", "CNNVD-2024-08", "", "Palo Alto PAN-OS 全局保护命令注入漏洞", "严重", 10.0, "NVD", "PAN-OS GlobalProtect 网关和门户存在命令注入漏洞，可导致 root 权限命令执行。", "pan-os,globalprotect", True, True, "升级 PAN-OS 10.2.9-h1+ / 11.0.4-h1+，启用威胁防护签名。", "2024-04-12"),
    ("CVE-2022-22965", "CNNVD-2022-31", "", "Spring Framework RCE（Spring4Shell）", "高危", 9.8, "NVD", "Spring Framework 数据绑定漏洞，在 JDK9+ Tomcat 部署下可远程代码执行。", "spring,java,tomcat", True, True, "升级 Spring Framework 5.3.18/5.2.20+。", "2022-04-01"),
    ("CNVD-2023-08743", "", "CNVD-2023-08743", "若依管理系统默认口令及 SQL 注入漏洞", "高危", 8.6, "CNVD", "若依(RuoYi)后台存在默认弱口令与 SQL 注入，可获取系统权限。", "若依,ruoyi", True, False, "修改默认口令，升级至 3.8.6+，开启访问控制。", "2023-05-18"),
    ("CNNVD-2024-567", "", "", "泛微 OA e-cology 远程代码执行漏洞", "高危", 9.0, "CNNVD", "泛微 e-cology 部分版本存在反序列化漏洞，攻击者可未授权执行任意代码。", "泛微,ecology", True, False, "升级至官方最新补丁版本，限制后台接口访问。", "2024-08-15"),
    ("CVE-2024-21762", "CNNVD-2024-12", "", "Fortinet FortiOS SSL-VPN 越界写入漏洞", "严重", 9.6, "NVD", "FortiOS SSL-VPN 存在越界写入漏洞，可被远程利用执行任意代码，已有在野利用。", "fortinet,ssl-vpn", True, True, "升级 FortiOS 至修复版本，禁用不必要的 SSL-VPN Web 模式。", "2024-02-09"),
    ("CVE-2023-38545", "CNNVD-2023-90", "", "cURL SOCKS5 堆溢出漏洞（CURL）", "高危", 8.8, "NVD", "curl SOCKS5 代理解析存在堆缓冲区溢出，可致远程代码执行。", "curl", False, False, "升级 curl 至 8.4.0+。", "2023-10-11"),
    ("CNVD-2022-66777", "", "CNVD-2022-66777", "ThinkPHP 多语言特性文件包含漏洞", "高危", 8.5, "CNVD", "ThinkPHP 开启多语言模式时可被利用包含任意文件。", "thinkphp,php", True, False, "关闭多语言切换功能或升级框架。", "2022-12-05"),
    ("CVE-2021-3156", "CNNVD-2021-19", "", "Sudo 堆溢出提权漏洞（Baron Samedit）", "高危", 7.8, "NVD", "sudo 1.8.2-1.8.31p2 / 1.9.0-1.9.5p1 存在堆溢出，本地用户可提权至 root。", "linux,sudo,centos", False, False, "升级 sudo 至 1.9.5p2+。", "2021-01-26"),
    ("CVE-2025-31200", "CNNVD-2025-42", "", "Confluence 数据中心未经授权访问漏洞", "高危", 8.9, "NVD", "Confluence Data Center 部分版本存在权限绕过漏洞，未认证攻击者可读取受限页面。", "confluence,atlassian", False, True, "升级 Confluence 至官方修复版本。", "2025-04-30"),
    ("CNVD-2024-39876", "", "CNVD-2024-39876", "深信服 SSL VPN 任意文件读取漏洞", "中危", 6.5, "CNVD", "深信服 VPN 部分版本存在任意文件读取，可泄露配置信息。", "深信服,vpn", False, False, "更新官方补丁，限制管理口暴露。", "2024-07-22"),
    ("CVE-2020-14882", "CNNVD-2020-58", "", "Oracle WebLogic 控制台未授权访问 RCE", "严重", 9.8, "NVD", "WebLogic Console 存在认证绕过结合 RCE，利用门槛低。", "weblogic,oracle,java", True, False, "升级 CPU 补丁，限制控制台访问来源。", "2020-10-21"),
    ("CVE-2024-6387", "CNNVD-2024-30", "", "OpenSSH 信号处理竞争条件漏洞（regreSSHion）", "高危", 8.1, "NVD", "OpenSSH 8.5p1-9.7p1 存在远程代码执行竞争条件（glibc Linux）。", "openssh,ssh,linux", False, False, "升级 OpenSSH 9.8p1+。", "2024-07-01"),
    ("CNNVD-2025-120", "", "", "用友 NC Cloud 反序列化漏洞", "高危", 8.9, "CNNVD", "用友 NC Cloud 部分接口存在反序列化漏洞，可未授权执行命令。", "用友,nc,java", True, False, "应用官方补丁，删除或限制缺陷接口。", "2025-06-18"),
    ("CVE-2022-26134", "CNNVD-2022-40", "", "Confluence OGNL 注入漏洞", "严重", 9.8, "NVD", "Confluence Server 存在未认证 OGNL 注入，可远程代码执行。", "confluence,atlassian", True, True, "升级至 7.4.17/7.13.7/7.17.4+。", "2022-06-02"),
    ("CNVD-2021-33454", "", "CNVD-2021-33454", "Coremail 邮件系统配置信息泄露漏洞", "中危", 5.3, "CNVD", "Coremail 存在配置文件泄露，可获取系统路径及账号信息。", "coremail,mail", True, False, "应用官方补丁，删除敏感配置入口。", "2021-05-12"),
    ("CVE-2023-4966", "CNNVD-2023-98", "", "Citrix NetScaler 会话令牌泄露漏洞（CitrixBleed）", "高危", 9.4, "NVD", "NetScaler ADC/Gateway 存在敏感信息泄露，可劫持会话，已被在野利用。", "citrix,netscaler", True, True, "升级 13.1-49.15+/14.1-25.53+，终止所有活跃会话。", "2023-10-18"),
    ("CVE-2019-0708", "CNNVD-2019-20", "", "Windows RDP 远程代码执行漏洞（BlueKeep）", "严重", 9.8, "NVD", "Windows RDP 服务存在远程代码执行漏洞，可蠕虫式传播。", "windows,rdp", True, False, "安装 KB 补丁，关闭不必要 RDP 暴露，启用 NLA。", "2019-05-14"),
    ("CNVD-2025-04321", "", "CNVD-2025-04321", "某小程序后端接口未授权访问漏洞", "中危", 6.0, "CNVD", "小程序后端接口缺少鉴权，可遍历用户数据。", "小程序,api", False, False, "补齐接口鉴权与限流。", "2025-02-20"),
]

INTEL = [
    ("CNNVD", "CNNVD 关于 Apache Log4j2 远程代码执行漏洞的预警", "http://www.cnnvd.org.cn", "CNNVD 发布 Log4j2 JNDI 注入漏洞预警，建议受影响单位立即排查升级。", "严重", "CVE-2021-44228", "2026-11-18"),
    ("CNVD", "CNVD 收录泛微 OA 远程代码执行漏洞（CNVD-2024-567XX）", "https://www.cnvd.org.cn", "泛微 e-cology 反序列化漏洞已被攻击利用，请部署官方补丁。", "高危", "", "2026-11-17"),
    ("360CERT", "360CERT 发布 Fortinet FortiOS 漏洞风险通告", "https://cert.360.cn/warning", "FortiOS SSL-VPN 越界写入漏洞在野利用，360 情报中心持续跟踪。", "严重", "CVE-2024-21762", "2026-11-16"),
    ("奇安信", "奇安信威胁情报中心：Cl0p 组织利用 MOVEit 漏洞攻击升温", "https://ti.qianxin.com/advisory", "近期观察到 Cl0p 针对国内单位 MOVEit 实例的批量扫描。", "高危", "CVE-2023-34362", "2026-11-15"),
    ("绿盟", "绿盟科技：Confluence 系列漏洞组合利用预警", "http://www.nsfocus.net", "攻击者组合利用 CVE-2022-26134 与未授权访问漏洞获取内网权限。", "高危", "CVE-2022-26134", "2026-11-14"),
    ("OSCS", "OSCS 漏洞库：若依管理系统默认口令风险提示", "https://oscs1024.com", "大量互联网暴露的若依后台仍使用默认口令。", "高危", "CNVD-2023-08743", "2026-11-13"),
    ("NVD", "NVD 新增 OpenSSH regreSSHion 漏洞分析数据", "https://nvd.nist.gov", "NVD 完成 CVE-2024-6387 的 CVSS 与 CPE 分析。", "高危", "CVE-2024-6387", "2026-11-12"),
    ("CNNVD", "CNNVD 关于 Microsoft Exchange 系列漏洞的通报", "http://www.cnnvd.org.cn", "建议排查 Exchange 在线服务代理配置。", "中危", "", "2026-11-11"),
    ("安全客", "安全客：2026 APT 年度趋势——供应链攻击占比上升", "https://www.anquanke.com", "APT 组织加大软件供应链投毒力度，建议建立软件物料清单。", "", "", "2026-11-10"),
    ("CNVD", "CNVD 收录 ThinkPHP 多语言文件包含漏洞利用代码", "https://www.cnvd.org.cn", "利用代码已在公开渠道传播，请相关单位尽快加固。", "高危", "CNVD-2022-66777", "2026-11-09"),
    ("360CERT", "360CERT：监测到针对 VPN 网关的大规模口令爆破活动", "https://cert.360.cn/warning", "多个僵尸网络联合对暴露 VPN 网关发起爆破。", "高危", "", "2026-11-08"),
    ("OSCS", "OSCS：Spring Framework 新版本修复多个中危问题", "https://oscs1024.com", "建议升级 Spring Framework 至 5.3.39+。", "中危", "", "2026-11-07"),
]

TASKS = [
    ("季度互联网资产暴露面核查", "全部互联网暴露资产（7 项）", "nuclei", "已完成", 100, "2026-11-10 09:00", "2026-11-10 11:32"),
    ("核心系统 POC 验证专项", "OA/邮件/业务申报系统", "poc-suite", "执行中", 60, "2026-11-19 01:30", ""),
    ("内网弱口令排查", "10.1.10.0/24", "weak-pass", "待执行", 0, "", ""),
]

FINDINGS = [
    (1, "oa.example.gov.cn", "泛微 OA e-cology 远程代码执行漏洞", "高危", "CNNVD-2024-567", "POST /api/ec/dev/... 反序列化探测响应 200 且回显执行结果", True, False, "admin"),
    (1, "oa.example.gov.cn", "若依管理系统默认口令及 SQL 注入漏洞", "高危", "CNVD-2023-08743", "后台 /login 使用 ruoyi/admin666 登录成功", True, False, "admin"),
    (1, "www.example.gov.cn", "Apache Log4j2 远程代码执行漏洞（Log4Shell）", "严重", "CVE-2021-44228", "JNDI 反连测试成功，dnslog 收到回连", True, False, "admin"),
    (1, "mail.example.gov.cn", "Coremail 邮件系统配置信息泄露漏洞", "中危", "CNVD-2021-33454", "配置入口可访问但未返回敏感字段", False, True, "admin"),
    (1, "60.10.2.15", "深信服 SSL VPN 任意文件读取漏洞", "中危", "CNVD-2024-39876", "接口返回 403，疑似已修补", False, True, "admin"),
    (1, "sb.example.gov.cn", "Spring Framework RCE（Spring4Shell）", "高危", "CVE-2022-22965", "Class.class 触发成功，确认可利用", True, False, ""),
]


def run_seed():
    Base.metadata.create_all(engine)
    from .skills_builtin import sync_builtin_skills
    sync_builtin_skills()
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(username="admin", password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                         display_name="安全管理员", role="admin"))
            db.add(User(username="analyst", password_hash=hash_password("Analyst@2026"),
                         display_name="安全分析员", role="analyst"))
            db.add(User(username="viewer", password_hash=hash_password("Viewer@2026"),
                         display_name="只读账号", role="viewer"))
            db.commit()
        if db.query(Asset).count() > 0:
            return
        for name, typ, value, dept, crit, icp, exp, fp in ASSETS:
            db.add(Asset(name=name, type=typ, value=value, owner_dept=dept,
                         criticality=crit, icp_no=icp, exposure=exp,
                         fingerprint=fp, last_scan_at="2026-11-10"))
        for cve, cnnvd, cnvd, title, sev, cvss, src, desc, kw, poc, wild, fix, pub in VULNS:
            db.add(Vulnerability(cve_id=cve, cnnvd_id=cnnvd, cnvd_id=cnvd,
                                 title=title, severity=sev, cvss=cvss, source=src,
                                 description=desc, affected_keywords=kw,
                                 poc_available=poc, exploited_in_wild=wild,
                                 fix_suggestion=fix, published_at=pub))
        for src, title, url, summary, sev, ref, pub in INTEL:
            db.add(IntelItem(source=src, title=title, url=url, summary=summary,
                             severity=sev, ref_id=ref, published_at=pub))
        for name, scope, eng, status, prog, st, ft in TASKS:
            db.add(ScanTask(name=name, target_scope=scope, engine=eng,
                            status=status, progress=prog, started_at=st, finished_at=ft))
        for tid, asset, title, sev, poc, ev, ver, fp, by in FINDINGS:
            db.add(Finding(task_id=tid, asset_value=asset, vuln_title=title,
                           severity=sev, poc_ref=poc, evidence=ev,
                           verified=ver, false_positive=fp, reviewed_by=by))
        db.commit()
    finally:
        db.close()
