import base64
import hashlib
import hmac
import json
import time
from datetime import datetime

import requests
from loguru import logger

from plugins.LLMBridge.bridge.reply import Reply, ReplyType
from plugins.LLMBridge.voice.voice import Voice

service = "asr"
host = "asr.tencentcloudapi.com"
version = "2019-06-14"
action = "SentenceRecognition"
algorithm = "TC3-HMAC-SHA256"


class TencentVoice(Voice):
    def __init__(self):
        self.secret_id = ""
        self.secret_key = ""

    def voiceToText(self, voice_file):

        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

        base64_voice = base64.b64encode(voice_file.getvalue()).decode('utf-8')
        payload = json.dumps({'EngSerViceType': '16k_zh', 'SourceType': 1, 'VoiceFormat': 'wav', 'Data': base64_voice})

        # ************* 步骤 1：拼接规范请求串 *************
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        ct = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{ct}\nhost:{host}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = (f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n"
                             f"{canonical_headers}\n{signed_headers}\n{hashed_request_payload}")

        # ************* 步骤 2：拼接待签名字符串 *************
        credential_scope = f"{date}/{service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

        # ************* 步骤 3：计算签名 *************
        secret_date = self.sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = self.sign(secret_date, service)
        secret_signing = self.sign(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # ************* 步骤 4：拼接 Authorization *************
        authorization = (f"{algorithm} Credential={self.secret_id}/{credential_scope}, "
                         f"SignedHeaders={signed_headers}, Signature={signature}")

        # ************* 步骤 5：构造并发起请求 *************
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version
        }
        reply = None
        try:
            response = requests.post(f"https://{host}/", headers=headers, data=payload)
            response.raise_for_status()  # 检查请求是否成功
            resp_json = response.json()
            logger.debug(f"腾讯语音语音识别结果：{resp_json}")
            reply = Reply(ReplyType.TEXT, resp_json.get('Response', {}).get('Result', ''))
        except requests.exceptions.RequestException as err:
            logger.error(f"腾讯语音语音识别请求失败: {err}")
            reply = Reply(ReplyType.ERROR, '腾讯语音语音识别请求失败')
        return reply

    def textToVoice(self, text):
        pass

    def sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

