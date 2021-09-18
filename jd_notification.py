#!/usr/local/bin/python
# -*- coding: utf-8 -*-
# @Time    : 2021/9/18 3:42 下午
# @File    : jd_notification.py
# @Project : jd_scripts
# @Desc    : 京东活动通知
import asyncio
import json
import time

import ujson
from urllib.parse import quote
import aiohttp
import moment

from config import USER_AGENT
from utils.jd_init import jd_init
from utils.console import println


@jd_init
class JdNotification:
    """
    统一消息通知
    """
    headers = {
        'user-agent': USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
        'host': 'api.m.jd.com'
    }

    async def request(self, session, url, body='', method='GET', json_data=None):
        """
        请求数据
        :param json_data:
        :param session:
        :param url:
        :param body:
        :param method:
        :return:
        """
        try:
            await asyncio.sleep(1)
            if method == 'GET':
                request_func = session.get
            else:
                request_func = session.post

            if json_data:
                response = await request_func(url=url, json=json_data)
            else:
                response = await request_func(url=url, data=body)

            text = await response.text()

            data = json.loads(text)

            return data

        except Exception as e:
            println('{}, 请求服务器失败, {}'.format(self.account, e.args))
            return {}

    async def get_bean_msg(self, session):
        """
        获取收入/支出京豆
        :param session:
        :return:
        """
        url = 'https://api.m.jd.com/client.action?functionId=getJingBeanBalanceDetail'

        total_bean = 0  # 京豆总数
        today_income = 0  # 今日收入
        today_used = 0  # 今日支出
        yesterday_income = 0  # 昨日收入
        yesterday_used = 0  # 昨日支出
        yesterday = moment.date(moment.now().sub('days', 1)).zero  # 昨天
        today = moment.date(moment.now()).zero  # 今天

        finished = False

        for page in range(1, 10):
            body = 'body={}&appid=ld'.format(quote(json.dumps({"pageSize": "20", "page": str(page)})))
            res = await self.request(session, url, body, method='POST')
            if not res.get('detailList', []):
                break
            item_list = res.get('detailList')

            for item in item_list:
                day = moment.date(item['date'], '%H:%M:%S').zero
                amount = int(item['amount'])
                if '退还京豆' in item.get('eventMassage', ''):
                    continue
                if day.diff(yesterday).days == 0:
                    if amount > 0:  # 收入
                        yesterday_income += amount
                    else:  # 支出
                        yesterday_used += -amount

                elif day.diff(yesterday).days >= 1:  # 昨天之前的日期跳过
                    finished = True
                    break

                if day.diff(today).days == 0:
                    if amount > 0:
                        today_income += amount
                    else:
                        today_used = -amount
            if finished:
                break

        url = 'https://me-api.jd.com/user_new/info/GetJDUserInfoUnion'
        session.headers.add('Host', 'me-api.jd.com')
        data = await self.request(session, url)
        if data:
            total_bean = data['data']['assetInfo']['beanNum']

        message = f'当前京豆总数:{total_bean} \n今日收入京豆:{today_income}\n' \
                  f'今日支出京豆:{today_used}\n昨日收入京豆:{yesterday_income}\n昨日支出京豆:{yesterday_used}'

        return message

    async def get_jd_farm_msg(self, session):
        """
        获取东东农场信息
        :param session:
        :return:
        """
        url = 'https://api.m.jd.com/client.action?functionId=initForFarm&body=%7B%22babelChannel%22%3A%22121%22%2C' \
              '%22lng%22%3A%22113.383803%22%2C%22lat%22%3A%2223.102671%22%2C%22sid%22%3A' \
              '%228e51862fd39a3498a6de0093dc06539w%22%2C%22un_area%22%3A%2219_1601_36953_50397%22%2C%22version%22' \
              '%3A14%2C%22channel%22%3A1%7D&appid=wh5'
        res = await self.request(session, url)

        data = res.get('farmUserPro', dict())

        award_name = data.get('name', '查询失败')
        award_percentage = round(data.get('treeEnergy', 0.0) / data.get('treeTotalEnergy', 0.1) * 100, 2)

        message = f'东东农场: {award_name}, 进度:{award_percentage}%'

        return message

    async def get_jd_earn_msg(self, session):
        """
        获取京东赚赚信息
        :param session:
        :return:
        """

        url = 'https://api.m.jd.com/client.action?functionId=interactTaskIndex&body=%7B%27mpVersion%27%3A+%273.4.0%27' \
              '%7D&client=wh5&clientVersion=9.1.0'

        res = await self.request(session, url)

        amount = round(int(res.get('data', dict()).get('totalNum', 0)) / 10000, 2)

        msg = f'京东赚赚: 可提现:{amount}￥'

        return msg

    async def get_jd_sec_coin_msg(self, session):
        """
        获取秒秒比信息
        :return:
        """
        session.headers.update({
            'referer': 'https://h5.m.jd.com/babelDiy/Zeus/2NUvze9e1uWf4amBhe1AV6ynmSuH/index.html',
            'origin': 'https://h5.m.jd.com',
        })

        url = 'https://api.m.jd.com/client.action?clientVersion=10.1.2&client=wh5&osVersion=&area=&networkType=wifi' \
              '&functionId=homePageV2&body=%7B%7D&appid=SecKill2020'

        res = await self.request(session, url)

        point = res.get('result', dict()).get('assignment', dict()).get('assignmentPoints', 0.0)

        amount = point / 1000

        msg = f'秒秒币: 数量:{point}, 可提现:{amount}￥'

        return msg

    async def get_jd_supermarket_msg(self, session):
        """
        获取东东超市蓝币信息
        :param session:
        :return:
        """
        session.headers.update({
            'origin': 'https://jdsupermarket.jd.com',
            'referer': 'https://jdsupermarket.jd.com/game/?tt={}'.format(int(time.time() * 1000)),
            'content-type': 'application/x-www-form-urlencoded',
        })
        url = 'https://api.m.jd.com/api?functionId=smtg_newHome&appid=jdsupermarket&clientVersion=8.0.0&client=m&t' \
              '=1631957189&body=%7B%22channel%22%3A+%221%22%7D'
        res = await self.request(session, url)

        blue_count = res.get('data', dict()).get('result', dict()).get('totalBlue', 0)

        msg = f'东东超市: 蓝币数量:{blue_count}'

        return msg

    async def get_jd_factory_msg(self, session):
        """
        获取东东工厂信息
        :param session:
        :return:
        """
        url = 'https://api.m.jd.com/client.action/?functionId=jdfactory_getHomeData&body=%7B%7D&client=wh5' \
              '&clientVersion=1.0.0'
        res = await self.request(session, url)

        data = res.get('data', dict()).get('result', dict()).get('factoryInfo', dict())

        name = data.get('name', '无')
        need_amount = int(data.get('totalScore', '0'))
        used_amount = int(data.get('useScore', '0'))
        remain_amount = int(data.get('remainScore', '0'))

        msg = f'东东工厂:  奖品:{name}, 投入电量:{used_amount}/{need_amount}, 剩余电量:{remain_amount}'

        return msg

    async def get_jd_car_msg(self, session):
        """
        获取京豆汽车信息
        :param session:
        :return:
        """
        session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "car-member.jd.com",
            "Referer": "https://h5.m.jd.com/babelDiy/Zeus/44bjzCpzH9GpspWeBzYSqBA7jEtP/index.html",
        })

        url = 'https://car-member.jd.com/api/v1/user/point?timestamp={}'.format(int(time.time()*1000))

        res = await self.request(session, url)

        point = res.get('data', dict()).get('remainPoint', 0)

        msg = f'京东汽车: 积分:{point}'

        return msg

    async def get_jd_cash_msg(self, session):
        """
        获取领现金信息
        :param session:
        :return:
        """
        url = 'https://api.m.jd.com/client.action?functionId=cash_homePage&clientVersion=10.1.2&build=89743&client' \
              '=android&openudid=a27b83d3d1dba1cc&uuid=a27b83d3d1dba1cc&aid=a27b83d3d1dba1cc&networkType=wifi' \
              '&harmonyOs=0&st=1631958646482&sign=58ebf3d09bb5d97b87d95e49e419a19b&sv=110&body=%7B%7D&'
        res = await self.request(session, url)

        total_amount = res.get('data', dict()).get('result', dict()).get('totalMoney', 0.0)

        msg = f'签到领现金: 当前金额:{total_amount}'

        return msg

    async def get_jd_cut_pet_msg(self, session):
        """
        获取东东萌宠信息
        :param session:
        :return:
        """
        url = 'https://api.m.jd.com/client.action?functionId=initPetTown&body=%7B%22version%22%3A%202%2C%20%22channel' \
              '%22%3A%20%22app%22%7D&appid=wh5&loginWQBiz=pet-town&clientVersion=9.0.4'
        res = await self.request(session, url)

        println(res)

    async def notify(self, session):
        """
        京东资产变动通知
        :param session:
        :return:
        """
        jd_farm_msg = await self.get_jd_farm_msg(session)
        jd_cash_msg = await self.get_jd_cash_msg(session)
        jd_earn_msg = await self.get_jd_earn_msg(session)
        jd_car_msg = await self.get_jd_car_msg(session)
        jd_factory_msg = await self.get_jd_factory_msg(session)
        jd_supermarket_msg = await self.get_jd_supermarket_msg(session)
        jd_sec_coin_msg = await self.get_jd_sec_coin_msg(session)
        bean_msg = await self.get_bean_msg(session)

        self.message = '\n'.join([
            bean_msg,
            jd_earn_msg,
            jd_cash_msg,
            jd_car_msg,
            jd_farm_msg,
            jd_factory_msg,
            jd_supermarket_msg,
            jd_sec_coin_msg,
        ])

    async def run(self):
        async with aiohttp.ClientSession(cookies=self.cookies, headers=self.headers,
                                         json_serialize=ujson.dumps) as session:
            await self.notify(session)


if __name__ == '__main__':
    from utils.process import process_start
    process_start(JdNotification, '消息通知')
