"""
实现了椭圆加密
"""

import utils
import random

# 一些神秘的数字，由 Bitcoin 定义
_a = 0x0000000000000000000000000000000000000000000000000000000000000000         # 椭圆曲线 a
_b = 0x0000000000000000000000000000000000000000000000000000000000000007         # 椭圆曲线 b
_p = 0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f         # 取模运算的模数
_r = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141         # 私钥不能大于 _r

_Gx = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798        # 椭圆曲线上固定一点 G 的 x
_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8        # 椭圆曲线上固定一点 G 的 y


class Curve_Encrypt:
    def __init__(self, _a, _b, _p, _r):
        self._a = _a
        self._b = _b
        self._p = _p
        self._r = _r

    """
    签名和验签过程
    签名：
    1. Alice 产生临时私密 r, 计算对应点 g 的横坐标 xrand
    2. Alice 计算 s = (h + k * xrand) / r, 其中， h 位消息，k 为私钥匙，r 为临时私钥，r = (h + k * xrand) / s
    3. Alice 将消息 h, 签名, 公钥 p 发给 Bob，签名 = xrand + s

    验证
    1. Bob 收到消息 h, 签名, 公钥 p，签名 = xrand + s
    2. 计算 (h / s) * G + (xrand / s) * p, 其中 p = kG
        推导：(h / s) * G + (xrand / s) * p = (h / s) * G + (k * rand / s) * G = [(h + k * rand) / s] * G = r * G
    3. 通过 r * G 是否等于 xrand
    """


    def sign(self, msg: str, private_key: int, G: tuple) -> tuple:
        m = int(utils.hash256(msg), 16)
        randNum = random.randint(1, _r)
        xRand, yRand = self.Emultiple(G, randNum)
        r = xRand % self._r # 临时私钥
        s = ((m + r * private_key) * self.__curve_mod_inv(randNum, self._r)) % self._r
        return r, s


    def sign_verify(self, msg: str, public_key: tuple, rs: tuple, G: tuple) -> bool:
        m = int(utils.hash256(msg), 16)
        w = self.__curve_mod_inv(rs[1], self._r)
        rx1, ry1 = self.Emultiple(G, (m * w) % self._r)
        rx2, ry2 = self.Emultiple(public_key, (rs[0] * w) % self._r)
        x, y = self.__curve_add((rx1, ry1), (rx2, ry2))
        return x == rs[0]


    def Emultiple(self, G: tuple, secret_key: int) -> tuple:
        """
        计算公钥
        :param G: 椭圆上的不动点，(x, y)
        :param secret_key: 私钥
        :return:
        """
        if secret_key == 0 or secret_key >= self._r:
            raise Exception("Invalid secret key")
        secret_key = str(bin(secret_key))[2:]   # 从第二位开始运算
        g = G
        for i in range(1, len(secret_key)):
            g = self.__curve_double(g)
            if secret_key[i] == '1':
                g = self.__curve_add(g, G)
        return g

    def parse(self, g: tuple):
        """
        解析最后生成的 g，根据官方文档，公钥有 33 位
        当 gy 是偶数时，第一位是 0x02, 当 gy 是奇数时， 第一位是 0x03
        后面32位是 gx 从第三位开始的后面所有
        :param g:
        :return: 公钥匙
        """
        if g[1] % 2 == 0:
            public_key = "02" + hex(g[0])[2:]
        else:
            public_key = "03" + hex(g[0])[2:]
        return public_key

    def get_address(self, secret_key: int, G: tuple):
        public = self.Emultiple(G, secret_key)
        sa = self.parse(public)
        tmpa = utils.hash256(sa)
        tmpa = utils.rip1(tmpa)
        tmpa_body = '00' + tmpa
        tmpa = tmpa_body
        tmpa = utils.hash256(tmpa)
        prefix = utils.hash256(tmpa)[:8]
        pro_address = tmpa_body + prefix
        return public, utils.base58(pro_address)

    # Private Method Below

    def __curve_mod_inv(self, m: int, p: int = -1) -> int:
        """
        求模逆元，x -> b ^ (-1) (mod p) = bx -> 1 (mod p)
        拓展欧几里得算法求模逆元, mx -> 1 (mod p) => mx + py -> 1 (mod p)
        :param m: 分母
        :return: 模逆元
        """
        if p == -1:
            p = self._p
        x, _, g = utils.ext_euclid(m, p)
        if (x * m) % p == 1:
            if x < 0:
                x += p
            return x
        else:
            raise Exception("Invalid input")

    def __curve_add(self, p: tuple, q: tuple) -> tuple:
        """
        椭圆加密加法，输入p为P点坐标，横坐标P[0]，纵坐标P[1]，q类似，输出为R点坐标(rx为横坐标、ry纵坐标)
        :param p: (x, y)
        :param q: (x, y)
        :return: (x, y)
        """
        lam = ((q[1] - p[1]) * self.__curve_mod_inv(q[0] - p[0])) % self._p
        rx = (lam ** 2 - p[0] - q[0]) % self._p
        ry = (lam * (p[0] - rx) - p[1]) % self._p
        return rx, ry

    def __curve_double(self, p: tuple) -> tuple:
        """
        椭圆加密乘法，等于过P点做椭圆曲线切线交椭圆的点关于X轴对称的点R
        :param p: (x, y)
        :return: (x, y)
        """
        lam = (((3 * (p[0] ** 2)) + self._a) * self.__curve_mod_inv(2 * p[1])) % self._p
        rx = (lam ** 2 - 2 * p[0]) % self._p
        ry = (lam * (p[0] - rx) - p[1]) % self._p
        return rx, ry


if __name__ == "__main__":
    G = (_Gx, _Gy)
    curve = Curve_Encrypt(_a, _b, _p, _r)
    secret_key = 0x18e14a7b6a307f426a94f8114701e7c8e774e7f9a47e2c2035db29a206321725
    pubk = curve.Emultiple(G, secret_key)
    h = "123123"
    signature = curve.sign(h, secret_key, G)
    print(signature)
    verify = curve.sign_verify(h, pubk, signature, G)
    print(verify)


