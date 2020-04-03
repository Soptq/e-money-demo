"""
实现了一些工具函数
"""
import hashlib
import json
import math

_a = 0x0000000000000000000000000000000000000000000000000000000000000000  # 椭圆曲线 a
_b = 0x0000000000000000000000000000000000000000000000000000000000000007  # 椭圆曲线 b
_p = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f  # 取模运算的模数
_r = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141  # 私钥不能大于 _r

_Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798  # 椭圆曲线上固定一点 G 的 x
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8  # 椭圆曲线上固定一点 G 的 y

def get_magic_param():
    return (_a, _b, _p, _r), (_Gx, _Gy)


def ext_euclid(a, b):
    """
    拓展欧几里得算法
    :param a:
    :param b:
    :return: ax + by = g, 返回 x, y, g
    """
    old_s, s = 1, 0
    old_t, t = 0, 1
    old_r, r = a, b
    if b == 0:
        return 1, 0, a
    else:
        while r != 0:
            q = old_r // r
            old_r, r = r, old_r - q * r
            old_s, s = s, old_s - q * s
            old_t, t = t, old_t - q * t
    return old_s, old_t, old_r


def hash256(s):
    return hashlib.sha256(json.dumps(s).encode()).hexdigest()


def hash256_double(s):
    return hashlib.sha256((hashlib.sha256(s).hexdigest()).encode()).hexdigest()


def generate_merkle(hash_list: list):
    """实现默克尔根"""
    if len(hash_list) == 1:
        return hash_list[0]
    upper_hash_list = []
    for i in range(0, len(hash_list) - 1, 2):
        upper_hash_list.append(merkle_hash(hash_list[i], hash_list[i + 1]))
    if len(hash_list) % 2 == 1:
        upper_hash_list.append(merkle_hash(hash_list[-1], hash_list[-1]))
    return generate_merkle(upper_hash_list)


def merkle_hash(a: str, b: str) -> str:
    c = (a + b).encode()
    c = hash256_double(c)
    return c


def rip1(a):
    a = json.dumps(a).encode()
    a = hashlib.new('ripemd160', a).hexdigest()
    return a


def base58(address_hex):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    b58_string = ''
    leading_zeros = len(address_hex) - len(address_hex.lstrip('0'))
    address_int = int(address_hex, 16)
    while address_int > 0:
        digit = address_int % 58
        digit_char = alphabet[digit]
        b58_string = digit_char + b58_string
        address_int //= 58
    ones = leading_zeros // 2
    for one in range(ones):
        b58_string = '1' + b58_string
    return b58_string


def c_logistic(n):
    return 64 * (1 / (1 + math.exp(1) ** (-n + 20)))

