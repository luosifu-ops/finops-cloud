"""统一响应格式"""


def ok(data=None, msg="success"):
    return {"code": 0, "msg": msg, "data": data}


def fail(msg="error", code=1, data=None):
    return {"code": code, "msg": msg, "data": data}
