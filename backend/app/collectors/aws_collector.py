# LogRaven — AWS Boto3 State and Log Ingestion Collector
# Collects live snapshots of AWS IAM, EC2/VPC, S3, KMS, and CloudTrail
# and streams CloudTrail events for 100% Deterministic (Non-AI) CSPM Rule Evaluation.

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger("lograven.collectors.aws")


def _calc_age_days(dt_val: Optional[datetime | str]) -> int:
    """Calculates age in whole days from a datetime or ISO string to now (UTC)."""
    if not dt_val:
        return 9999
    try:
        if isinstance(dt_val, str):
            # Parse ISO or standard credential report date
            clean_str = dt_val.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(clean_str)
        else:
            parsed = dt_val
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, (now - parsed).days)
    except Exception:
        return 9999


class AWSStateAndLogCollector:
    """
    Collects configuration snapshots and CloudTrail event streams from AWS
    for 100% Deterministic CSPM Evaluation.
    """

    def __init__(
        self,
        session: Optional[boto3.Session] = None,
        region_name: str = "us-east-1",
        iam_client: Optional[Any] = None,
        ec2_client: Optional[Any] = None,
        s3_client: Optional[Any] = None,
        kms_client: Optional[Any] = None,
        cloudtrail_client: Optional[Any] = None,
        elbv2_client: Optional[Any] = None,
        elb_client: Optional[Any] = None,
        logs_client: Optional[Any] = None,
        apigateway_client: Optional[Any] = None,
        apigatewayv2_client: Optional[Any] = None,
        lambda_client: Optional[Any] = None,
        rds_client: Optional[Any] = None,
        kinesis_client: Optional[Any] = None,
        eks_client: Optional[Any] = None,
        ecs_client: Optional[Any] = None,
        ecr_client: Optional[Any] = None,
        dynamodb_client: Optional[Any] = None,
        elasticache_client: Optional[Any] = None,
        secretsmanager_client: Optional[Any] = None,
        acm_client: Optional[Any] = None,
        wafv2_client: Optional[Any] = None,
        cloudfront_client: Optional[Any] = None,
        route53_client: Optional[Any] = None,
        sqs_client: Optional[Any] = None,
        sns_client: Optional[Any] = None,
    ):
        self.region_name = region_name
        self.session = session or boto3.Session(region_name=region_name)
        self._iam = iam_client
        self._ec2 = ec2_client
        self._s3 = s3_client
        self._kms = kms_client
        self._cloudtrail = cloudtrail_client
        self._elbv2 = elbv2_client
        self._elb = elb_client
        self._logs = logs_client
        self._apigateway = apigateway_client
        self._apigatewayv2 = apigatewayv2_client
        self._lambda = lambda_client
        self._rds = rds_client
        self._kinesis = kinesis_client
        self._eks = eks_client
        self._ecs = ecs_client
        self._ecr = ecr_client
        self._dynamodb = dynamodb_client
        self._elasticache = elasticache_client
        self._secretsmanager = secretsmanager_client
        self._acm = acm_client
        self._wafv2 = wafv2_client
        self._cloudfront = cloudfront_client
        self._route53 = route53_client
        self._sqs = sqs_client
        self._sns = sns_client

    @property
    def iam(self) -> Any:
        if self._iam is None:
            self._iam = self.session.client("iam", region_name=self.region_name)
        return self._iam

    @property
    def ec2(self) -> Any:
        if self._ec2 is None:
            self._ec2 = self.session.client("ec2", region_name=self.region_name)
        return self._ec2

    @property
    def elbv2(self) -> Any:
        if self._elbv2 is None:
            self._elbv2 = self.session.client("elbv2", region_name=self.region_name)
        return self._elbv2

    @property
    def elb(self) -> Any:
        if self._elb is None:
            self._elb = self.session.client("elb", region_name=self.region_name)
        return self._elb

    @property
    def logs(self) -> Any:
        if self._logs is None:
            self._logs = self.session.client("logs", region_name=self.region_name)
        return self._logs

    @property
    def apigateway(self) -> Any:
        if self._apigateway is None:
            self._apigateway = self.session.client("apigateway", region_name=self.region_name)
        return self._apigateway

    @property
    def apigatewayv2(self) -> Any:
        if self._apigatewayv2 is None:
            self._apigatewayv2 = self.session.client("apigatewayv2", region_name=self.region_name)
        return self._apigatewayv2

    @property
    def lambda_client(self) -> Any:
        if self._lambda is None:
            self._lambda = self.session.client("lambda", region_name=self.region_name)
        return self._lambda

    @property
    def rds(self) -> Any:
        if self._rds is None:
            self._rds = self.session.client("rds", region_name=self.region_name)
        return self._rds

    @property
    def kinesis(self) -> Any:
        if self._kinesis is None:
            self._kinesis = self.session.client("kinesis", region_name=self.region_name)
        return self._kinesis

    @property
    def s3(self) -> Any:
        if self._s3 is None:
            self._s3 = self.session.client("s3", region_name=self.region_name)
        return self._s3

    @property
    def kms(self) -> Any:
        if self._kms is None:
            self._kms = self.session.client("kms", region_name=self.region_name)
        return self._kms

    @property
    def cloudtrail(self) -> Any:
        if self._cloudtrail is None:
            self._cloudtrail = self.session.client("cloudtrail", region_name=self.region_name)
        return self._cloudtrail

    @property
    def eks(self) -> Any:
        if self._eks is None:
            self._eks = self.session.client("eks", region_name=self.region_name)
        return self._eks

    @property
    def ecs(self) -> Any:
        if self._ecs is None:
            self._ecs = self.session.client("ecs", region_name=self.region_name)
        return self._ecs

    @property
    def ecr(self) -> Any:
        if self._ecr is None:
            self._ecr = self.session.client("ecr", region_name=self.region_name)
        return self._ecr

    @property
    def dynamodb(self) -> Any:
        if self._dynamodb is None:
            self._dynamodb = self.session.client("dynamodb", region_name=self.region_name)
        return self._dynamodb

    @property
    def elasticache(self) -> Any:
        if self._elasticache is None:
            self._elasticache = self.session.client("elasticache", region_name=self.region_name)
        return self._elasticache

    @property
    def secretsmanager(self) -> Any:
        if self._secretsmanager is None:
            self._secretsmanager = self.session.client("secretsmanager", region_name=self.region_name)
        return self._secretsmanager

    @property
    def acm(self) -> Any:
        if self._acm is None:
            self._acm = self.session.client("acm", region_name=self.region_name)
        return self._acm

    @property
    def wafv2(self) -> Any:
        if self._wafv2 is None:
            self._wafv2 = self.session.client("wafv2", region_name=self.region_name)
        return self._wafv2

    @property
    def cloudfront(self) -> Any:
        if self._cloudfront is None:
            self._cloudfront = self.session.client("cloudfront", region_name="us-east-1")
        return self._cloudfront

    @property
    def route53(self) -> Any:
        if self._route53 is None:
            self._route53 = self.session.client("route53", region_name="us-east-1")
        return self._route53

    @property
    def sqs(self) -> Any:
        if self._sqs is None:
            self._sqs = self.session.client("sqs", region_name=self.region_name)
        return self._sqs

    @property
    def sns(self) -> Any:
        if self._sns is None:
            self._sns = self.session.client("sns", region_name=self.region_name)
        return self._sns

    # ── IAM State Collection ─────────────────────────────────────────────────

    def collect_iam_state(self) -> List[Dict[str, Any]]:
        """
        Collects IAM user credential health (MFA, rotation age) and role/user policy ASTs.
        """
        resources: List[Dict[str, Any]] = []

        # 1. Credential Report
        cred_report_data: Dict[str, Dict[str, Any]] = {}
        try:
            resp = self.iam.get_credential_report()
            content = resp.get("Content", b"")
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                uname = row.get("user")
                if not uname:
                    continue
                pw_enabled = row.get("password_enabled") == "true"
                mfa_active = row.get("mfa_active") == "true"
                pw_age = _calc_age_days(row.get("password_last_changed")) if pw_enabled else 0
                ak1_age = _calc_age_days(row.get("access_key_1_last_rotated")) if row.get("access_key_1_active") == "true" else 0
                ak2_age = _calc_age_days(row.get("access_key_2_last_rotated")) if row.get("access_key_2_active") == "true" else 0
                cred_age = max(pw_age, ak1_age, ak2_age)

                cred_report_data[uname] = {
                    "urn": row.get("arn") or f"arn:aws:iam:::user/{uname}",
                    "native_id": uname,
                    "id": uname,
                    "user": uname,
                    "arn": row.get("arn"),
                    "mfa_active": mfa_active,
                    "password_enabled": pw_enabled,
                    "password_age_days": pw_age,
                    "access_key_age_days": max(ak1_age, ak2_age),
                    "credential_age_days": cred_age,
                    "access_key_1_active": row.get("access_key_1_active") == "true",
                    "access_key_2_active": row.get("access_key_2_active") == "true",
                }
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not retrieve IAM credential report: %s", exc)

        # 2. IAM Users
        try:
            users_resp = self.iam.list_users()
            for u in users_resp.get("Users", []):
                uname = u.get("UserName")
                u_arn = u.get("Arn") or f"arn:aws:iam:::user/{uname}"
                item = cred_report_data.get(uname, {
                    "urn": u_arn,
                    "native_id": uname,
                    "id": uname,
                    "user": uname,
                    "arn": u_arn,
                    "mfa_active": False,
                    "credential_age_days": 0,
                })

                # Fetch inline policies
                inline_stmts = []
                try:
                    pol_names = self.iam.list_user_policies(UserName=uname).get("PolicyNames", [])
                    for p_name in pol_names:
                        p_doc = self.iam.get_user_policy(UserName=uname, PolicyName=p_name).get("PolicyDocument")
                        if isinstance(p_doc, str):
                            p_doc = json.loads(p_doc)
                        if isinstance(p_doc, dict):
                            stmts = p_doc.get("Statement", [])
                            if isinstance(stmts, list):
                                inline_stmts.extend(stmts)
                            elif isinstance(stmts, dict):
                                inline_stmts.append(stmts)
                except Exception:
                    pass

                p_doc_full = {"Version": "2012-10-17", "Statement": inline_stmts}
                item["Statement"] = inline_stmts
                item["PolicyDocument"] = p_doc_full
                item["PolicyDocuments"] = [p_doc_full]
                resources.append(item)
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not list IAM users: %s", exc)

        # If no users were found via list_users but credential report had entries, add them
        existing_urns = {r.get("urn") for r in resources}
        for uname, c_item in cred_report_data.items():
            if c_item["urn"] not in existing_urns:
                c_item["Statement"] = []
                c_item["PolicyDocument"] = {"Version": "2012-10-17", "Statement": []}
                resources.append(c_item)

        # 3. IAM Roles
        try:
            roles_resp = self.iam.list_roles()
            for r in roles_resp.get("Roles", []):
                rname = r.get("RoleName")
                r_arn = r.get("Arn") or f"arn:aws:iam:::role/{rname}"
                statements: List[Dict[str, Any]] = []

                # Fetch inline policies
                try:
                    inline_pols = self.iam.list_role_policies(RoleName=rname).get("PolicyNames", [])
                    for p_name in inline_pols:
                        p_doc = self.iam.get_role_policy(RoleName=rname, PolicyName=p_name).get("PolicyDocument")
                        if isinstance(p_doc, str):
                            p_doc = json.loads(p_doc)
                        if isinstance(p_doc, dict):
                            stmts = p_doc.get("Statement", [])
                            if isinstance(stmts, list):
                                statements.extend(stmts)
                            elif isinstance(stmts, dict):
                                statements.append(stmts)
                except Exception:
                    pass

                r_doc_full = {"Version": "2012-10-17", "Statement": statements}
                resources.append({
                    "urn": r_arn,
                    "native_id": r.get("RoleId") or rname,
                    "id": rname,
                    "RoleName": rname,
                    "arn": r_arn,
                    "Statement": statements,
                    "PolicyDocument": r_doc_full,
                    "PolicyDocuments": [r_doc_full],
                })
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not list IAM roles: %s", exc)

        return resources

    # ── EC2 Instances & VPC Security Groups ──────────────────────────────────

    def get_ec2_regions(self) -> List[str]:
        """Returns list of enabled AWS regions for EC2 inspection."""
        try:
            if hasattr(self.ec2, "describe_regions"):
                resp = self.ec2.describe_regions(Filters=[{"Name": "opt-in-status", "Values": ["opt-in-not-required", "opted-in"]}])
                regions = [r["RegionName"] for r in resp.get("Regions", []) if "RegionName" in r]
                if regions:
                    return regions
        except Exception as exc:
            logger.debug("Could not describe regions, falling back to [%s]: %s", self.region_name, exc)
        return [self.region_name]

    def collect_ec2_instances(self) -> List[Dict[str, Any]]:
        """
        Collects EC2 virtual machine instances across active AWS regions.
        Extracts InstanceId, instance type, state, public/private IPs, VpcId, subnet, and tags.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_instances_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._ec2 is not None:
                    client = self.ec2
                elif self.session is not None:
                    client = self.session.client("ec2", region_name=region)
                else:
                    client = self.ec2

                if hasattr(client, "get_paginator"):
                    paginator = client.get_paginator("describe_instances")
                    pages = paginator.paginate()
                else:
                    pages = [client.describe_instances()]

                for page in pages:
                    for resv in page.get("Reservations", []):
                        owner_id = resv.get("OwnerId", "")
                        for inst in resv.get("Instances", []):
                            inst_id = inst.get("InstanceId")
                            if not inst_id:
                                continue
                            tags_list = inst.get("Tags", [])
                            tags_dict = {t["Key"]: t["Value"] for t in tags_list if "Key" in t and "Value" in t}
                            name = tags_dict.get("Name") or inst_id
                            state_obj = inst.get("State", {})
                            state_name = state_obj.get("Name", "unknown") if isinstance(state_obj, dict) else str(state_obj)
                            pub_ip = inst.get("PublicIpAddress")
                            priv_ip = inst.get("PrivateIpAddress")

                            reg_items.append({
                                "urn": f"arn:aws:ec2:{region}:{owner_id}:instance/{inst_id}",
                                "native_id": inst_id,
                                "id": inst_id,
                                "InstanceId": inst_id,
                                "name": name,
                                "resource_type": "instance",
                                "service": "EC2",
                                "region": region,
                                "InstanceType": inst.get("InstanceType"),
                                "State": state_name,
                                "state": state_name,
                                "PublicIpAddress": pub_ip,
                                "public_ip": pub_ip,
                                "PrivateIpAddress": priv_ip,
                                "private_ip": priv_ip,
                                "VpcId": inst.get("VpcId"),
                                "SubnetId": inst.get("SubnetId"),
                                "ImageId": inst.get("ImageId"),
                                "Architecture": inst.get("Architecture"),
                                "SecurityGroups": inst.get("SecurityGroups", []),
                                "tags": tags_dict,
                                "open_to_world": bool(pub_ip and state_name == "running"),
                            })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe EC2 instances in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_instances_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_instances_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    def collect_security_groups(self) -> List[Dict[str, Any]]:
        """
        Collects VPC Security Groups with Ingress/Egress rules for CID 41/42 inspection.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_sgs_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._ec2 is not None:
                    client = self.ec2
                elif self.session is not None:
                    client = self.session.client("ec2", region_name=region)
                else:
                    client = self.ec2

                sgs = client.describe_security_groups().get("SecurityGroups", [])
                for sg in sgs:
                    sg_id = sg.get("GroupId")
                    reg_items.append({
                        "urn": f"arn:aws:ec2:{region}::security-group/{sg_id}",
                        "native_id": sg_id,
                        "id": sg_id,
                        "GroupId": sg_id,
                        "GroupName": sg.get("GroupName"),
                        "name": sg.get("GroupName") or sg_id,
                        "resource_type": "security_group",
                        "service": "SECURITY_GROUP",
                        "region": region,
                        "Description": sg.get("Description"),
                        "VpcId": sg.get("VpcId"),
                        "IpPermissions": sg.get("IpPermissions", []),
                        "IpPermissionsEgress": sg.get("IpPermissionsEgress", []),
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe security groups in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_sgs_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_sgs_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Elastic Load Balancers (ALB, NLB, Gateway, Classic) ──────────────────

    def collect_load_balancers(self) -> List[Dict[str, Any]]:
        """
        Collects Application, Network, Gateway, and Classic Load Balancers across active AWS regions.
        Extracts LoadBalancerArn, Name, DNSName, Type, Scheme, State, VpcId, SecurityGroups, and tags.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_lbs_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []

            # 1. elbv2 (Application, Network, Gateway Load Balancers)
            try:
                if region == self.region_name and self._elbv2 is not None:
                    client_v2 = self._elbv2
                elif self.session is not None:
                    client_v2 = self.session.client("elbv2", region_name=region)
                else:
                    client_v2 = self.elbv2

                if hasattr(client_v2, "get_paginator"):
                    paginator = client_v2.get_paginator("describe_load_balancers")
                    pages = paginator.paginate()
                else:
                    pages = [client_v2.describe_load_balancers()]

                for page in pages:
                    for lb in page.get("LoadBalancers", []):
                        arn = lb.get("LoadBalancerArn", "")
                        name = lb.get("LoadBalancerName", "")
                        dns = lb.get("DNSName", "")
                        scheme = lb.get("Scheme", "internet-facing")
                        lb_type = lb.get("Type", "application")
                        state_val = lb.get("State", {}).get("Code", "active") if isinstance(lb.get("State"), dict) else str(lb.get("State", "active"))
                        sg_ids = lb.get("SecurityGroups", [])

                        reg_items.append({
                            "urn": arn or f"arn:aws:elasticloadbalancing:{region}::loadbalancer/{name}",
                            "native_id": name or arn,
                            "id": name or arn,
                            "name": name,
                            "resource_type": "load_balancer",
                            "service": "LOAD_BALANCER",
                            "region": region,
                            "LoadBalancerArn": arn,
                            "DNSName": dns,
                            "dns_name": dns,
                            "Scheme": scheme,
                            "scheme": scheme,
                            "Type": lb_type,
                            "lb_type": lb_type,
                            "State": state_val,
                            "state": state_val,
                            "VpcId": lb.get("VpcId"),
                            "AvailabilityZones": lb.get("AvailabilityZones", []),
                            "SecurityGroups": sg_ids,
                            "SecurityGroupIds": sg_ids,
                            "open_to_world": scheme == "internet-facing",
                        })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe elbv2 load balancers in region %s: %s", region, exc)

            # 2. Classic ELB
            try:
                if region == self.region_name and self._elb is not None:
                    client_v1 = self._elb
                elif self.session is not None:
                    client_v1 = self.session.client("elb", region_name=region)
                else:
                    client_v1 = self.elb

                if hasattr(client_v1, "get_paginator"):
                    paginator = client_v1.get_paginator("describe_load_balancers")
                    pages = paginator.paginate()
                else:
                    pages = [client_v1.describe_load_balancers()]

                for page in pages:
                    for lb in page.get("LoadBalancerDescriptions", []):
                        name = lb.get("LoadBalancerName", "")
                        dns = lb.get("DNSName", "")
                        scheme = lb.get("Scheme", "internet-facing")
                        sg_ids = lb.get("SecurityGroups", [])

                        reg_items.append({
                            "urn": f"arn:aws:elasticloadbalancing:{region}::loadbalancer/classic/{name}",
                            "native_id": name,
                            "id": name,
                            "name": name,
                            "resource_type": "load_balancer",
                            "service": "LOAD_BALANCER",
                            "region": region,
                            "DNSName": dns,
                            "dns_name": dns,
                            "Scheme": scheme,
                            "scheme": scheme,
                            "Type": "classic",
                            "lb_type": "classic",
                            "State": "active",
                            "state": "active",
                            "VpcId": lb.get("VPCId"),
                            "Instances": lb.get("Instances", []),
                            "SecurityGroups": sg_ids,
                            "SecurityGroupIds": sg_ids,
                            "open_to_world": scheme == "internet-facing",
                        })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe classic load balancers in region %s: %s", region, exc)

            return reg_items

        if len(regions) == 1:
            return _fetch_lbs_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_lbs_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── S3 Buckets ───────────────────────────────────────────────────────────

    def collect_s3_buckets(self) -> List[Dict[str, Any]]:
        """
        Collects S3 Buckets, Server-Side Encryption (SSE) settings, and Public Access Block configuration.
        """
        resources: List[Dict[str, Any]] = []
        try:
            buckets = self.s3.list_buckets().get("Buckets", [])
            for b in buckets:
                bname = b.get("Name")
                if not bname:
                    continue

                sse_conf = None
                enc_enabled = False
                kms_key_id = None
                try:
                    enc_resp = self.s3.get_bucket_encryption(Bucket=bname)
                    sse_conf = enc_resp.get("ServerSideEncryptionConfiguration")
                    if sse_conf:
                        enc_enabled = True
                        rules = sse_conf.get("Rules", [])
                        if rules:
                            default_enc = rules[0].get("ApplyServerSideEncryptionByDefault", {})
                            kms_key_id = default_enc.get("KMSMasterKeyId")
                except Exception:
                    pass

                pab_conf = None
                try:
                    pab_resp = self.s3.get_public_access_block(Bucket=bname)
                    pab_conf = pab_resp.get("PublicAccessBlockConfiguration")
                except Exception:
                    pass

                pol_doc = None
                try:
                    pol_resp = self.s3.get_bucket_policy(Bucket=bname)
                    pol_str = pol_resp.get("Policy")
                    if pol_str:
                        pol_doc = json.loads(pol_str) if isinstance(pol_str, str) else pol_str
                except Exception:
                    pass

                resources.append({
                    "urn": f"arn:aws:s3:::{bname}",
                    "native_id": bname,
                    "id": bname,
                    "Name": bname,
                    "BucketName": bname,
                    "ServerSideEncryptionConfiguration": sse_conf,
                    "encryption_enabled": enc_enabled,
                    "kms_key_id": kms_key_id,
                    "PublicAccessBlockConfiguration": pab_conf,
                    "Policy": pol_doc,
                    "PolicyDocument": pol_doc,
                })
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not list S3 buckets: %s", exc)
        return resources

    # ── KMS Keys ─────────────────────────────────────────────────────────────

    def collect_kms_keys(self) -> List[Dict[str, Any]]:
        """
        Collects KMS keys and checks automatic key rotation status.
        """
        resources: List[Dict[str, Any]] = []
        try:
            keys = self.kms.list_keys().get("Keys", [])
            for k in keys:
                kid = k.get("KeyId")
                if not kid:
                    continue
                meta = {}
                rot_enabled = False
                try:
                    meta = self.kms.describe_key(KeyId=kid).get("KeyMetadata", {})
                except Exception:
                    pass
                try:
                    rot_enabled = self.kms.get_key_rotation_status(KeyId=kid).get("KeyRotationEnabled", False)
                except Exception:
                    pass

                resources.append({
                    "urn": meta.get("Arn") or f"arn:aws:kms:{self.region_name}::key/{kid}",
                    "native_id": kid,
                    "id": kid,
                    "KeyId": kid,
                    "Arn": meta.get("Arn"),
                    "KeyManager": meta.get("KeyManager"),
                    "Enabled": meta.get("Enabled", True),
                    "KeyRotationEnabled": rot_enabled,
                    "KeyMetadata": meta,
                })
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not list KMS keys: %s", exc)
        return resources

    # ── CloudTrail Trails ────────────────────────────────────────────────────

    def collect_cloudtrail_trails(self) -> List[Dict[str, Any]]:
        """
        Collects CloudTrail trails and logging configuration.
        """
        resources: List[Dict[str, Any]] = []
        try:
            trails = self.cloudtrail.describe_trails().get("trailList", [])
            for t in trails:
                tname = t.get("Name")
                tarn = t.get("TrailARN") or f"arn:aws:cloudtrail:{self.region_name}::trail/{tname}"
                resources.append({
                    "urn": tarn,
                    "native_id": tname,
                    "id": tname,
                    "Name": tname,
                    "TrailARN": tarn,
                    "S3BucketName": t.get("S3BucketName"),
                    "IncludeGlobalServiceEvents": t.get("IncludeGlobalServiceEvents", False),
                    "IsMultiRegionTrail": t.get("IsMultiRegionTrail", False),
                    "LogFileValidationEnabled": t.get("LogFileValidationEnabled", False),
                    "KmsKeyId": t.get("KmsKeyId"),
                })
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not describe CloudTrail trails: %s", exc)
        return resources

    # ── CloudTrail Events ────────────────────────────────────────────────────

    def collect_cloudtrail_events(
        self,
        lookup_attributes: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Fetches recent CloudTrail events via lookup_events API.
        """
        events: List[Dict[str, Any]] = []
        try:
            kwargs: Dict[str, Any] = {"MaxResults": max_results}
            if lookup_attributes:
                kwargs["LookupAttributes"] = lookup_attributes

            resp = self.cloudtrail.lookup_events(**kwargs)
            for raw_evt in resp.get("Events", []):
                ct_json = raw_evt.get("CloudTrailEvent", "{}")
                if isinstance(ct_json, str):
                    try:
                        ct_parsed = json.loads(ct_json)
                    except Exception:
                        ct_parsed = {}
                else:
                    ct_parsed = ct_json

                events.append(ct_parsed)
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.warning("Could not lookup CloudTrail events: %s", exc)
        return events

    # ── CloudWatch Log Groups ────────────────────────────────────────────────

    def collect_log_groups(self) -> List[Dict[str, Any]]:
        """
        Collects CloudWatch Log Groups across active regions and checks retention and encryption.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_logs_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._logs is not None:
                    client = self._logs
                elif self.session is not None:
                    client = self.session.client("logs", region_name=region)
                else:
                    client = self.logs

                if hasattr(client, "get_paginator"):
                    paginator = client.get_paginator("describe_log_groups")
                    pages = paginator.paginate()
                else:
                    pages = [client.describe_log_groups()]

                for page in pages:
                    for lg in page.get("logGroups", []):
                        lg_name = lg.get("logGroupName", "")
                        arn = lg.get("arn", "")
                        retention = lg.get("retentionInDays")
                        kms_key = lg.get("kmsKeyId")

                        reg_items.append({
                            "urn": arn or f"arn:aws:logs:{region}::log-group:{lg_name}",
                            "native_id": lg_name,
                            "id": lg_name,
                            "name": lg_name,
                            "resource_type": "log_group",
                            "service": "LOG_GROUP",
                            "region": region,
                            "logGroupName": lg_name,
                            "retentionInDays": retention,
                            "kmsKeyId": kms_key,
                            "storedBytes": lg.get("storedBytes", 0),
                            "encryption_enabled": bool(kms_key),
                            "never_expire": retention is None,
                        })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe log groups in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_logs_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_logs_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── API Gateway (REST & HTTP/WebSocket) ──────────────────────────────────

    def collect_api_gateways(self) -> List[Dict[str, Any]]:
        """
        Collects API Gateway v1 (REST) and v2 (HTTP/WebSocket) APIs across active regions.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_apis_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []

            # 1. v1 REST APIs
            try:
                if region == self.region_name and self._apigateway is not None:
                    client_v1 = self._apigateway
                elif self.session is not None:
                    client_v1 = self.session.client("apigateway", region_name=region)
                else:
                    client_v1 = self.apigateway

                apis = client_v1.get_rest_apis().get("items", [])
                for api in apis:
                    api_id = api.get("id", "")
                    name = api.get("name", api_id)
                    reg_items.append({
                        "urn": f"arn:aws:apigateway:{region}::/restapis/{api_id}",
                        "native_id": api_id,
                        "id": api_id,
                        "name": name,
                        "resource_type": "rest_api",
                        "service": "API_GATEWAY",
                        "region": region,
                        "api_id": api_id,
                        "protocol": "REST",
                        "endpointConfiguration": api.get("endpointConfiguration", {}),
                        "tags": api.get("tags") or {},
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not get REST APIs in region %s: %s", region, exc)

            # 2. v2 HTTP / WebSocket APIs
            try:
                if region == self.region_name and self._apigatewayv2 is not None:
                    client_v2 = self._apigatewayv2
                elif self.session is not None:
                    client_v2 = self.session.client("apigatewayv2", region_name=region)
                else:
                    client_v2 = self.apigatewayv2

                apis_v2 = client_v2.get_apis().get("Items", [])
                for api in apis_v2:
                    api_id = api.get("ApiId", "")
                    name = api.get("Name", api_id)
                    protocol = api.get("ProtocolType", "HTTP")
                    endpoint = api.get("ApiEndpoint", "")
                    reg_items.append({
                        "urn": f"arn:aws:apigateway:{region}::/apis/{api_id}",
                        "native_id": api_id,
                        "id": api_id,
                        "name": name,
                        "resource_type": "http_api",
                        "service": "API_GATEWAY",
                        "region": region,
                        "api_id": api_id,
                        "protocol": protocol,
                        "endpoint": endpoint,
                        "tags": api.get("Tags") or {},
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not get HTTP/WebSocket APIs in region %s: %s", region, exc)

            return reg_items

        if len(regions) == 1:
            return _fetch_apis_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_apis_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── AWS Lambda Functions ─────────────────────────────────────────────────

    def collect_lambda_functions(self) -> List[Dict[str, Any]]:
        """
        Collects AWS Lambda serverless functions across active regions.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_lambdas_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._lambda is not None:
                    client = self._lambda
                elif self.session is not None:
                    client = self.session.client("lambda", region_name=region)
                else:
                    client = self.lambda_client

                if hasattr(client, "get_paginator"):
                    paginator = client.get_paginator("list_functions")
                    pages = paginator.paginate()
                else:
                    pages = [client.list_functions()]

                for page in pages:
                    for fn in page.get("Functions", []):
                        fn_name = fn.get("FunctionName", "")
                        fn_arn = fn.get("FunctionArn", "")
                        reg_items.append({
                            "urn": fn_arn or f"arn:aws:lambda:{region}::function:{fn_name}",
                            "native_id": fn_name,
                            "id": fn_name,
                            "name": fn_name,
                            "resource_type": "function",
                            "service": "LAMBDA",
                            "region": region,
                            "FunctionName": fn_name,
                            "Runtime": fn.get("Runtime"),
                            "Role": fn.get("Role"),
                            "Handler": fn.get("Handler"),
                            "Timeout": fn.get("Timeout"),
                            "MemorySize": fn.get("MemorySize"),
                            "VpcConfig": fn.get("VpcConfig"),
                        })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list Lambda functions in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_lambdas_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_lambdas_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── RDS Database Instances ───────────────────────────────────────────────

    def collect_rds_instances(self) -> List[Dict[str, Any]]:
        """
        Collects RDS Database Instances and clusters across active regions.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_rds_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._rds is not None:
                    client = self._rds
                elif self.session is not None:
                    client = self.session.client("rds", region_name=region)
                else:
                    client = self.rds

                if hasattr(client, "get_paginator"):
                    paginator = client.get_paginator("describe_db_instances")
                    pages = paginator.paginate()
                else:
                    pages = [client.describe_db_instances()]

                for page in pages:
                    for db in page.get("DBInstances", []):
                        db_id = db.get("DBInstanceIdentifier", "")
                        db_arn = db.get("DBInstanceArn", "")
                        reg_items.append({
                            "urn": db_arn or f"arn:aws:rds:{region}::db:{db_id}",
                            "native_id": db_id,
                            "id": db_id,
                            "name": db_id,
                            "resource_type": "db_instance",
                            "service": "RDS",
                            "region": region,
                            "Engine": db.get("Engine"),
                            "EngineVersion": db.get("EngineVersion"),
                            "MultiAZ": db.get("MultiAZ", False),
                            "StorageEncrypted": db.get("StorageEncrypted", False),
                            "PubliclyAccessible": db.get("PubliclyAccessible", False),
                            "KmsKeyId": db.get("KmsKeyId"),
                        })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe RDS instances in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_rds_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_rds_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Kinesis Data Streams ─────────────────────────────────────────────────

    def collect_kinesis_streams(self) -> List[Dict[str, Any]]:
        """
        Collects Kinesis Data Streams across active regions, checking KMS encryption and retention periods.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_kinesis_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._kinesis is not None:
                    client = self._kinesis
                elif self.session is not None:
                    client = self.session.client("kinesis", region_name=region)
                else:
                    client = self.kinesis

                stream_names: List[str] = []
                if hasattr(client, "list_streams"):
                    resp = client.list_streams()
                    stream_names = list(resp.get("StreamNames", []))
                    while resp.get("HasMoreStreams", False):
                        last_name = stream_names[-1] if stream_names else None
                        if not last_name:
                            break
                        resp = client.list_streams(ExclusiveStartStreamName=last_name)
                        stream_names.extend(resp.get("StreamNames", []))

                for s_name in stream_names:
                    summary = {}
                    try:
                        sum_resp = client.describe_stream_summary(StreamName=s_name)
                        summary = sum_resp.get("StreamDescriptionSummary", {})
                    except Exception:
                        try:
                            desc_resp = client.describe_stream(StreamName=s_name)
                            summary = desc_resp.get("StreamDescription", {})
                        except Exception:
                            pass

                    s_arn = summary.get("StreamARN") or f"arn:aws:kinesis:{region}::stream/{s_name}"
                    enc_type = summary.get("EncryptionType", "NONE")
                    kms_key_id = summary.get("KeyId")
                    retention_hours = summary.get("RetentionPeriodHours", 24)
                    status = summary.get("StreamStatus", "ACTIVE")
                    open_shards = summary.get("OpenShardCount", 1)

                    reg_items.append({
                        "urn": s_arn,
                        "native_id": s_name,
                        "id": s_name,
                        "name": s_name,
                        "resource_type": "data_stream",
                        "service": "KINESIS",
                        "region": region,
                        "StreamName": s_name,
                        "StreamARN": s_arn,
                        "StreamStatus": status,
                        "RetentionPeriodHours": retention_hours,
                        "EncryptionType": enc_type,
                        "KeyId": kms_key_id,
                        "OpenShardCount": open_shards,
                        "encryption_enabled": enc_type == "KMS",
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list Kinesis streams in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_kinesis_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_kinesis_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon EKS (Elastic Kubernetes Service) ──────────────────────────────

    def collect_eks_clusters(self) -> List[Dict[str, Any]]:
        """
        Collects EKS Kubernetes clusters, control plane logging, endpoint exposure, and KMS encryption.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_eks_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._eks is not None:
                    client = self._eks
                elif self.session is not None:
                    client = self.session.client("eks", region_name=region)
                else:
                    client = self.eks

                cluster_names = client.list_clusters().get("clusters", [])
                for c_name in cluster_names:
                    try:
                        c_resp = client.describe_cluster(name=c_name)
                        cl = c_resp.get("cluster", {})
                        c_arn = cl.get("arn") or f"arn:aws:eks:{region}::cluster/{c_name}"
                        vpc_cfg = cl.get("resourcesVpcConfig", {})
                        enc_cfg = cl.get("encryptionConfig", [])
                        logging_cfg = cl.get("logging", {}).get("clusterLogging", [])

                        has_kms = bool(enc_cfg)
                        pub_endpoint = vpc_cfg.get("endpointPublicAccess", True)
                        priv_endpoint = vpc_cfg.get("endpointPrivateAccess", False)

                        reg_items.append({
                            "urn": c_arn,
                            "native_id": c_name,
                            "id": c_name,
                            "name": c_name,
                            "resource_type": "cluster",
                            "service": "EKS",
                            "region": region,
                            "cluster_name": c_name,
                            "version": cl.get("version"),
                            "status": cl.get("status"),
                            "endpoint": cl.get("endpoint"),
                            "roleArn": cl.get("roleArn"),
                            "endpointPublicAccess": pub_endpoint,
                            "endpointPrivateAccess": priv_endpoint,
                            "publicAccessCidrs": vpc_cfg.get("publicAccessCidrs", []),
                            "clusterLogging": logging_cfg,
                            "encryptionConfig": enc_cfg,
                            "encryption_enabled": has_kms,
                        })
                    except Exception as c_exc:
                        logger.debug("Could not describe EKS cluster %s in region %s: %s", c_name, region, c_exc)
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list EKS clusters in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_eks_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_eks_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon ECS (Elastic Container Service & Tasks / Pods) ───────────────

    def collect_ecs_resources(self) -> List[Dict[str, Any]]:
        """
        Collects ECS container clusters, running tasks (containers/pods equivalent), and task definitions.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_ecs_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._ecs is not None:
                    client = self._ecs
                elif self.session is not None:
                    client = self.session.client("ecs", region_name=region)
                else:
                    client = self.ecs

                cluster_arns = client.list_clusters().get("clusterArns", [])
                for cl_arn in cluster_arns:
                    cl_name = cl_arn.split("/")[-1]
                    reg_items.append({
                        "urn": cl_arn,
                        "native_id": cl_name,
                        "id": cl_name,
                        "name": cl_name,
                        "resource_type": "cluster",
                        "service": "ECS",
                        "region": region,
                        "clusterArn": cl_arn,
                        "clusterName": cl_name,
                    })

                    # Discover running Tasks (the ECS equivalent of Kubernetes Pods)
                    try:
                        task_arns = client.list_tasks(cluster=cl_arn).get("taskArns", [])
                        if task_arns:
                            for chunk_start in range(0, min(len(task_arns), 100), 100):
                                chunk = task_arns[chunk_start:chunk_start + 100]
                                desc_tasks = client.describe_tasks(cluster=cl_arn, tasks=chunk).get("tasks", [])
                                for t in desc_tasks:
                                    t_arn = t.get("taskArn", "")
                                    t_id = t_arn.split("/")[-1]
                                    containers = t.get("containers", [])
                                    reg_items.append({
                                        "urn": t_arn,
                                        "native_id": t_id,
                                        "id": t_id,
                                        "name": f"task-{t_id[:12]}",
                                        "resource_type": "task",
                                        "service": "ECS",
                                        "region": region,
                                        "clusterArn": cl_arn,
                                        "taskDefinitionArn": t.get("taskDefinitionArn"),
                                        "launchType": t.get("launchType"),
                                        "lastStatus": t.get("lastStatus"),
                                        "desiredStatus": t.get("desiredStatus"),
                                        "cpu": t.get("cpu"),
                                        "memory": t.get("memory"),
                                        "containers": containers,
                                        "container_count": len(containers),
                                    })
                    except Exception as t_exc:
                        logger.debug("Could not list/describe ECS tasks for cluster %s: %s", cl_name, t_exc)

            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list ECS clusters in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_ecs_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_ecs_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon ECR (Elastic Container Registry) ──────────────────────────────

    def collect_ecr_repositories(self) -> List[Dict[str, Any]]:
        """
        Collects ECR Container Registries, checking scan-on-push, tag immutability, and KMS encryption.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_ecr_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._ecr is not None:
                    client = self._ecr
                elif self.session is not None:
                    client = self.session.client("ecr", region_name=region)
                else:
                    client = self.ecr

                repos = client.describe_repositories().get("repositories", [])
                for r in repos:
                    r_name = r.get("repositoryName", "")
                    r_arn = r.get("repositoryArn") or f"arn:aws:ecr:{region}::repository/{r_name}"
                    scan_cfg = r.get("imageScanningConfiguration", {})
                    enc_cfg = r.get("encryptionConfiguration", {})
                    mutability = r.get("imageTagMutability", "MUTABLE")

                    reg_items.append({
                        "urn": r_arn,
                        "native_id": r_name,
                        "id": r_name,
                        "name": r_name,
                        "resource_type": "repository",
                        "service": "ECR",
                        "region": region,
                        "repositoryName": r_name,
                        "repositoryUri": r.get("repositoryUri"),
                        "scanOnPush": scan_cfg.get("scanOnPush", False),
                        "imageTagMutability": mutability,
                        "isImmutable": mutability == "IMMUTABLE",
                        "encryptionType": enc_cfg.get("encryptionType", "AES256"),
                        "kmsKey": enc_cfg.get("kmsKey"),
                        "encryption_enabled": enc_cfg.get("encryptionType") == "KMS",
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe ECR repositories in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_ecr_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_ecr_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon DynamoDB ──────────────────────────────────────────────────────

    def collect_dynamodb_tables(self) -> List[Dict[str, Any]]:
        """
        Collects DynamoDB tables, continuous backups (PITR), deletion protection, and SSE encryption.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_dynamo_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._dynamodb is not None:
                    client = self._dynamodb
                elif self.session is not None:
                    client = self.session.client("dynamodb", region_name=region)
                else:
                    client = self.dynamodb

                table_names = client.list_tables().get("TableNames", [])
                for t_name in table_names:
                    try:
                        desc = client.describe_table(TableName=t_name).get("Table", {})
                        t_arn = desc.get("TableArn") or f"arn:aws:dynamodb:{region}::table/{t_name}"
                        sse = desc.get("SSEDescription", {})
                        is_enc = sse.get("Status") == "ENABLED"

                        pitr_enabled = False
                        try:
                            cb_resp = client.describe_continuous_backups(TableName=t_name)
                            pitr_desc = cb_resp.get("ContinuousBackupsDescription", {}).get("PointInTimeRecoveryDescription", {})
                            pitr_enabled = pitr_desc.get("PointInTimeRecoveryStatus") == "ENABLED"
                        except Exception:
                            pass

                        reg_items.append({
                            "urn": t_arn,
                            "native_id": t_name,
                            "id": t_name,
                            "name": t_name,
                            "resource_type": "table",
                            "service": "DYNAMODB",
                            "region": region,
                            "TableName": t_name,
                            "TableStatus": desc.get("TableStatus"),
                            "ItemCount": desc.get("ItemCount", 0),
                            "TableSizeBytes": desc.get("TableSizeBytes", 0),
                            "DeletionProtectionEnabled": desc.get("DeletionProtectionEnabled", False),
                            "PointInTimeRecoveryEnabled": pitr_enabled,
                            "SSEDescription": sse,
                            "encryption_enabled": is_enc,
                        })
                    except Exception as t_exc:
                        logger.debug("Could not describe DynamoDB table %s in region %s: %s", t_name, region, t_exc)
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list DynamoDB tables in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_dynamo_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_dynamo_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon ElastiCache (Redis & Memcached) ────────────────────────────────

    def collect_elasticache_clusters(self) -> List[Dict[str, Any]]:
        """
        Collects ElastiCache clusters, checking encryption at rest, transit encryption, and auth tokens.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_cache_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._elasticache is not None:
                    client = self._elasticache
                elif self.session is not None:
                    client = self.session.client("elasticache", region_name=region)
                else:
                    client = self.elasticache

                clusters = client.describe_cache_clusters().get("CacheClusters", [])
                for cl in clusters:
                    cl_id = cl.get("CacheClusterId", "")
                    cl_arn = cl.get("ARN") or f"arn:aws:elasticache:{region}::cluster:{cl_id}"
                    reg_items.append({
                        "urn": cl_arn,
                        "native_id": cl_id,
                        "id": cl_id,
                        "name": cl_id,
                        "resource_type": "cluster",
                        "service": "ELASTICACHE",
                        "region": region,
                        "CacheClusterId": cl_id,
                        "Engine": cl.get("Engine"),
                        "EngineVersion": cl.get("EngineVersion"),
                        "CacheNodeType": cl.get("CacheNodeType"),
                        "NumCacheNodes": cl.get("NumCacheNodes", 1),
                        "AtRestEncryptionEnabled": cl.get("AtRestEncryptionEnabled", False),
                        "TransitEncryptionEnabled": cl.get("TransitEncryptionEnabled", False),
                        "AuthTokenEnabled": cl.get("AuthTokenEnabled", False),
                        "encryption_enabled": cl.get("AtRestEncryptionEnabled", False),
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not describe ElastiCache clusters in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_cache_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_cache_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── AWS Secrets Manager ──────────────────────────────────────────────────

    def collect_secrets_manager_secrets(self) -> List[Dict[str, Any]]:
        """
        Collects AWS Secrets Manager secrets, checking automatic rotation and KMS CMK encryption.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_secrets_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._secretsmanager is not None:
                    client = self._secretsmanager
                elif self.session is not None:
                    client = self.session.client("secretsmanager", region_name=region)
                else:
                    client = self.secretsmanager

                secrets = client.list_secrets().get("SecretList", [])
                for s in secrets:
                    s_name = s.get("Name", "")
                    s_arn = s.get("ARN") or f"arn:aws:secretsmanager:{region}::secret:{s_name}"
                    kms_key = s.get("KmsKeyId")
                    rot_enabled = s.get("RotationEnabled", False)

                    reg_items.append({
                        "urn": s_arn,
                        "native_id": s_name,
                        "id": s_name,
                        "name": s_name,
                        "resource_type": "secret",
                        "service": "SECRETS_MANAGER",
                        "region": region,
                        "Name": s_name,
                        "Description": s.get("Description"),
                        "KmsKeyId": kms_key,
                        "RotationEnabled": rot_enabled,
                        "LastRotatedDate": s.get("LastRotatedDate"),
                        "LastAccessedDate": s.get("LastAccessedDate"),
                        "encryption_enabled": bool(kms_key),
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list Secrets Manager secrets in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_secrets_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_secrets_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── AWS Certificate Manager (ACM) ────────────────────────────────────────

    def collect_acm_certificates(self) -> List[Dict[str, Any]]:
        """
        Collects ACM SSL/TLS certificates across active regions, checking expiry and key strength.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_acm_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._acm is not None:
                    client = self._acm
                elif self.session is not None:
                    client = self.session.client("acm", region_name=region)
                else:
                    client = self.acm

                cert_summaries = client.list_certificates().get("CertificateSummaryList", [])
                for sum_item in cert_summaries:
                    c_arn = sum_item.get("CertificateArn", "")
                    d_name = sum_item.get("DomainName", "")
                    detail = {}
                    try:
                        detail = client.describe_certificate(CertificateArn=c_arn).get("Certificate", {})
                    except Exception:
                        pass

                    not_after = detail.get("NotAfter")
                    expiry_days = _calc_age_days(not_after) if not_after else 9999

                    reg_items.append({
                        "urn": c_arn,
                        "native_id": c_arn.split("/")[-1] if "/" in c_arn else d_name,
                        "id": d_name,
                        "name": d_name,
                        "resource_type": "certificate",
                        "service": "ACM",
                        "region": region,
                        "CertificateArn": c_arn,
                        "DomainName": d_name,
                        "Status": detail.get("Status", sum_item.get("Status")),
                        "Type": detail.get("Type"),
                        "KeyAlgorithm": detail.get("KeyAlgorithm"),
                        "NotAfter": not_after,
                        "days_until_expiry": expiry_days,
                        "InUseBy": detail.get("InUseBy", []),
                    })
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list ACM certificates in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_acm_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_acm_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── AWS WAF (v2 Web ACLs) ────────────────────────────────────────────────

    def collect_waf_acls(self) -> List[Dict[str, Any]]:
        """
        Collects WAF v2 Web ACLs across regional and CloudFront scopes.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_waf_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._wafv2 is not None:
                    client = self._wafv2
                elif self.session is not None:
                    client = self.session.client("wafv2", region_name=region)
                else:
                    client = self.wafv2

                # Regional Web ACLs
                regional_acls = client.list_web_acls(Scope="REGIONAL").get("WebACLs", [])
                for acl in regional_acls:
                    a_name = acl.get("Name", "")
                    a_id = acl.get("Id", "")
                    a_arn = acl.get("ARN") or f"arn:aws:wafv2:{region}::regional/webacl/{a_name}/{a_id}"
                    reg_items.append({
                        "urn": a_arn,
                        "native_id": a_id,
                        "id": a_id,
                        "name": a_name,
                        "resource_type": "web_acl",
                        "service": "WAF",
                        "region": region,
                        "Scope": "REGIONAL",
                        "WebACLId": a_id,
                    })

                # CloudFront scope (available in us-east-1)
                if region == "us-east-1":
                    try:
                        cf_acls = client.list_web_acls(Scope="CLOUDFRONT").get("WebACLs", [])
                        for acl in cf_acls:
                            a_name = acl.get("Name", "")
                            a_id = acl.get("Id", "")
                            a_arn = acl.get("ARN") or f"arn:aws:wafv2:global::cloudfront/webacl/{a_name}/{a_id}"
                            reg_items.append({
                                "urn": a_arn,
                                "native_id": a_id,
                                "id": a_id,
                                "name": a_name,
                                "resource_type": "web_acl",
                                "service": "WAF",
                                "region": "global",
                                "Scope": "CLOUDFRONT",
                                "WebACLId": a_id,
                            })
                    except Exception:
                        pass
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list WAFv2 Web ACLs in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_waf_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_waf_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon CloudFront (CDN Distributions) ─────────────────────────────────

    def collect_cloudfront_distributions(self) -> List[Dict[str, Any]]:
        """
        Collects CloudFront CDN distributions, checking HTTPS enforcement, TLS version, and WAF protection.
        """
        resources: List[Dict[str, Any]] = []
        try:
            resp = self.cloudfront.list_distributions()
            items = resp.get("DistributionList", {}).get("Items", [])
            for d in items:
                d_id = d.get("Id", "")
                d_arn = d.get("ARN") or f"arn:aws:cloudfront::distribution/{d_id}"
                dom_name = d.get("DomainName", "")
                v_cert = d.get("ViewerCertificate", {})
                cache_behav = d.get("DefaultCacheBehavior", {})
                web_acl = d.get("WebACLId", "")

                proto_policy = cache_behav.get("ViewerProtocolPolicy", "")
                enforces_https = proto_policy in ("redirect-to-https", "https-only")
                min_protocol = v_cert.get("MinimumProtocolVersion", "SSLv3")

                resources.append({
                    "urn": d_arn,
                    "native_id": d_id,
                    "id": d_id,
                    "name": dom_name or d_id,
                    "resource_type": "distribution",
                    "service": "CLOUD_FRONT",
                    "region": "global",
                    "DistributionId": d_id,
                    "DomainName": dom_name,
                    "Status": d.get("Status"),
                    "Enabled": d.get("Enabled", False),
                    "ViewerProtocolPolicy": proto_policy,
                    "enforces_https": enforces_https,
                    "MinimumProtocolVersion": min_protocol,
                    "WebACLId": web_acl,
                    "has_waf": bool(web_acl),
                })
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.debug("Could not list CloudFront distributions: %s", exc)
        return resources

    # ── Amazon Route 53 (DNS Hosted Zones) ───────────────────────────────────

    def collect_route53_hosted_zones(self) -> List[Dict[str, Any]]:
        """
        Collects Route 53 public and private DNS hosted zones.
        """
        resources: List[Dict[str, Any]] = []
        try:
            zones = self.route53.list_hosted_zones().get("HostedZones", [])
            for z in zones:
                z_id = z.get("Id", "").replace("/hostedzone/", "")
                z_name = z.get("Name", "").rstrip(".")
                z_arn = f"arn:aws:route53:::hostedzone/{z_id}"
                cfg = z.get("Config", {})

                resources.append({
                    "urn": z_arn,
                    "native_id": z_id,
                    "id": z_id,
                    "name": z_name,
                    "resource_type": "hosted_zone",
                    "service": "ROUTE_53",
                    "region": "global",
                    "HostedZoneId": z_id,
                    "ZoneName": z_name,
                    "PrivateZone": cfg.get("PrivateZone", False),
                    "ResourceRecordSetCount": z.get("ResourceRecordSetCount", 0),
                })
        except (ClientError, BotoCoreError, Exception) as exc:
            logger.debug("Could not list Route 53 hosted zones: %s", exc)
        return resources

    # ── Amazon SQS (Simple Queue Service) ────────────────────────────────────

    def collect_sqs_queues(self) -> List[Dict[str, Any]]:
        """
        Collects SQS queues, checking KMS server-side encryption and dead-letter queues.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_sqs_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._sqs is not None:
                    client = self._sqs
                elif self.session is not None:
                    client = self.session.client("sqs", region_name=region)
                else:
                    client = self.sqs

                queue_urls = client.list_queues().get("QueueUrls", [])
                for q_url in queue_urls:
                    q_name = q_url.split("/")[-1]
                    try:
                        attrs = client.get_queue_attributes(QueueUrl=q_url, AttributeNames=["All"]).get("Attributes", {})
                        q_arn = attrs.get("QueueArn") or f"arn:aws:sqs:{region}::{q_name}"
                        kms_key = attrs.get("KmsMasterKeyId")
                        sse_sqs = attrs.get("SqsManagedSseEnabled") == "true"
                        is_enc = bool(kms_key) or sse_sqs

                        reg_items.append({
                            "urn": q_arn,
                            "native_id": q_name,
                            "id": q_name,
                            "name": q_name,
                            "resource_type": "queue",
                            "service": "SQS",
                            "region": region,
                            "QueueUrl": q_url,
                            "QueueArn": q_arn,
                            "KmsMasterKeyId": kms_key,
                            "SqsManagedSseEnabled": sse_sqs,
                            "encryption_enabled": is_enc,
                            "RedrivePolicy": attrs.get("RedrivePolicy"),
                            "VisibilityTimeout": attrs.get("VisibilityTimeout"),
                        })
                    except Exception as q_exc:
                        logger.debug("Could not get attributes for SQS queue %s: %s", q_name, q_exc)
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list SQS queues in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_sqs_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_sqs_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Amazon SNS (Simple Notification Service) ─────────────────────────────

    def collect_sns_topics(self) -> List[Dict[str, Any]]:
        """
        Collects SNS notification topics, checking KMS encryption and policy restrictions.
        """
        resources: List[Dict[str, Any]] = []
        regions = self.get_ec2_regions()

        def _fetch_sns_for_region(region: str) -> List[Dict[str, Any]]:
            reg_items: List[Dict[str, Any]] = []
            try:
                if region == self.region_name and self._sns is not None:
                    client = self._sns
                elif self.session is not None:
                    client = self.session.client("sns", region_name=region)
                else:
                    client = self.sns

                topics = client.list_topics().get("Topics", [])
                for t in topics:
                    t_arn = t.get("TopicArn", "")
                    t_name = t_arn.split(":")[-1]
                    try:
                        attrs = client.get_topic_attributes(TopicArn=t_arn).get("Attributes", {})
                        kms_key = attrs.get("KmsMasterKeyId")
                        reg_items.append({
                            "urn": t_arn,
                            "native_id": t_name,
                            "id": t_name,
                            "name": t_name,
                            "resource_type": "topic",
                            "service": "SNS",
                            "region": region,
                            "TopicArn": t_arn,
                            "KmsMasterKeyId": kms_key,
                            "encryption_enabled": bool(kms_key),
                            "Policy": attrs.get("Policy"),
                        })
                    except Exception as t_exc:
                        logger.debug("Could not get attributes for SNS topic %s: %s", t_name, t_exc)
            except (ClientError, BotoCoreError, Exception) as exc:
                logger.debug("Could not list SNS topics in region %s: %s", region, exc)
            return reg_items

        if len(regions) == 1:
            return _fetch_sns_for_region(regions[0])

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=min(8, len(regions))) as pool:
            futures = [pool.submit(_fetch_sns_for_region, reg) for reg in regions]
            for f in as_completed(futures):
                try:
                    resources.extend(f.result())
                except Exception:
                    pass

        return resources

    # ── Unified Collector ───────────────────────────────────────────────────

    def collect_all_resources(self, services: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Gathers resources across IAM, EC2, SECURITY_GROUP, LOAD_BALANCER, API_GATEWAY, LOG_GROUP, LAMBDA, RDS, KINESIS, EKS, ECS, ECR, DYNAMODB, ELASTICACHE, SECRETS_MANAGER, ACM, WAF, CLOUD_FRONT, ROUTE_53, SQS, SNS, S3, KMS, and CloudTrail.
        Returns a dictionary keyed by uppercase Service name for DeterministicComplianceGrader.
        """
        target_services = [s.upper() for s in services] if services else None

        collected: Dict[str, List[Dict[str, Any]]] = {
            "IAM": [],
            "EC2": [],
            "SECURITY_GROUP": [],
            "LOAD_BALANCER": [],
            "API_GATEWAY": [],
            "LOG_GROUP": [],
            "LAMBDA": [],
            "RDS": [],
            "KINESIS": [],
            "EKS": [],
            "ECS": [],
            "ECR": [],
            "DYNAMODB": [],
            "ELASTICACHE": [],
            "SECRETS_MANAGER": [],
            "ACM": [],
            "WAF": [],
            "CLOUD_FRONT": [],
            "ROUTE_53": [],
            "SQS": [],
            "SNS": [],
            "VPC": [],
            "S3": [],
            "KMS": [],
            "CLOUD_TRAIL": [],
        }

        if target_services is None or "IAM" in target_services:
            collected["IAM"] = self.collect_iam_state()

        if target_services is None or "EC2" in target_services:
            collected["EC2"] = self.collect_ec2_instances()

        if target_services is None or "SECURITY_GROUP" in target_services or "VPC" in target_services:
            sgs = self.collect_security_groups()
            collected["SECURITY_GROUP"] = sgs
            collected["VPC"] = sgs

        if target_services is None or "LOAD_BALANCER" in target_services or "ELB" in target_services:
            collected["LOAD_BALANCER"] = self.collect_load_balancers()

        if target_services is None or "LOG_GROUP" in target_services or "LOGS" in target_services:
            collected["LOG_GROUP"] = self.collect_log_groups()

        if target_services is None or "API_GATEWAY" in target_services:
            collected["API_GATEWAY"] = self.collect_api_gateways()

        if target_services is None or "LAMBDA" in target_services:
            collected["LAMBDA"] = self.collect_lambda_functions()

        if target_services is None or "RDS" in target_services:
            collected["RDS"] = self.collect_rds_instances()

        if target_services is None or "KINESIS" in target_services or "STREAM" in target_services:
            collected["KINESIS"] = self.collect_kinesis_streams()

        if target_services is None or "EKS" in target_services or "KUBERNETES" in target_services:
            collected["EKS"] = self.collect_eks_clusters()

        if target_services is None or "ECS" in target_services or "CONTAINER" in target_services or "POD" in target_services:
            collected["ECS"] = self.collect_ecs_resources()

        if target_services is None or "ECR" in target_services or "REGISTRY" in target_services:
            collected["ECR"] = self.collect_ecr_repositories()

        if target_services is None or "DYNAMODB" in target_services or "DYNAMO_DB" in target_services:
            collected["DYNAMODB"] = self.collect_dynamodb_tables()

        if target_services is None or "ELASTICACHE" in target_services or "REDIS" in target_services:
            collected["ELASTICACHE"] = self.collect_elasticache_clusters()

        if target_services is None or "SECRETS_MANAGER" in target_services or "SECRETS" in target_services:
            collected["SECRETS_MANAGER"] = self.collect_secrets_manager_secrets()

        if target_services is None or "ACM" in target_services or "CERTIFICATE" in target_services:
            collected["ACM"] = self.collect_acm_certificates()

        if target_services is None or "WAF" in target_services:
            collected["WAF"] = self.collect_waf_acls()

        if target_services is None or "CLOUD_FRONT" in target_services or "CLOUDFRONT" in target_services or "CDN" in target_services:
            collected["CLOUD_FRONT"] = self.collect_cloudfront_distributions()

        if target_services is None or "ROUTE_53" in target_services or "ROUTE53" in target_services or "DNS" in target_services:
            collected["ROUTE_53"] = self.collect_route53_hosted_zones()

        if target_services is None or "SQS" in target_services or "QUEUE" in target_services:
            collected["SQS"] = self.collect_sqs_queues()

        if target_services is None or "SNS" in target_services or "TOPIC" in target_services:
            collected["SNS"] = self.collect_sns_topics()

        if target_services is None or "S3" in target_services:
            collected["S3"] = self.collect_s3_buckets()

        if target_services is None or "KMS" in target_services:
            collected["KMS"] = self.collect_kms_keys()

        if target_services is None or "CLOUD_TRAIL" in target_services:
            collected["CLOUD_TRAIL"] = self.collect_cloudtrail_trails()

        return collected
