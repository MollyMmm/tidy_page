# -*- encoding:utf-8 -*-
from bs4 import BeautifulSoup
import urlparse
import requests
import re
import math
import posixpath
import bs4
import chardet
import traceback
import HTMLParser


def _take_out_list(Data, target_type):
    """拆解嵌套列表"""

    def _break_up_list(data, List):
        for item in data:
            if isinstance(item, target_type):
                List.append(item)
            else:
                _break_up_list(item, List)

    temporary_list = []
    _break_up_list(Data, temporary_list)
    temporary_list = [i for i in temporary_list if i]
    return temporary_list


class EYE:
    def __init__(self, url, header=None, timeout=60, separator="\n", keep_gif=False, smallest_length=2,
                 word_with_format=False, img_with_format=True, shortest_length=18, encoding=None, with_date=False):
        self.url = url
        self.header = header
        self.timeout = timeout
        self.separator = separator
        self.keep_gif = keep_gif
        self.smallest_length = smallest_length
        self.word_with_format = word_with_format
        self.img_with_format = img_with_format
        self.shortest_length = shortest_length
        self.encoding = encoding
        self.with_date = with_date

        self.summary = None
        self.title = None
        self.date = None
        self.elements = {
            "state": 1
        }

    regexps = {
        "unlikelyCandidates": re.compile(r"combx|comment|community|disqus|extra|foot|header|enu|remark|rss|shoutbox|"
                                         r"sidebar|sponsor|ad-break|agegate|pagination|pager|popup|tweet|twitter"),
        "okMaybeItsACandidate": re.compile(r"and|article|body|column|main|shadow"),
        "positive": re.compile(r"article|body|content|entry|hentry|main|page|pagination|post|text|blog|story"),
        "negative": re.compile(r"combx|comment|com|contact|foot|footer|footnote|masthead|media|meta|outbrain|promo|"
                               r"related|scroll|shoutbox|sidebar|sponsor|shopping|tags|tool|widget|recommend|clearfix"),
        # com-
        "extraneous": re.compile(r"print|archive|comment|discuss|e[\-]?mail|share|reply|all|login|sign|single"),
        "divToPElements": re.compile(r"<(a|blockquote|dl|div|img|ol|p|pre|table|ul|span|b|strong)"),
        "trim": re.compile(r"^\s+|\s+$"),
        "normalize": re.compile(r"\s{2,}"),
        "videos": re.compile(r"http://(www\.)?(youtube|vimeo)\.com"),
        "skipFootnoteLink": re.compile(r"^\s*(\[?[a-z0-9]{1,2}\]?|^|edit|citation needed)\s*$"),
        "nextLink": re.compile(r"(next|weiter|continue|>([^|]|$)|»([^|]|$))"),
        "prevLink": re.compile(r"(prev|earl|old|new|<|«)"),
        "url": re.compile(
            r'(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:'
            r'[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|'
            r'[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'),
        "brackets": re.compile(r"<.*?>"),
        "symbol": re.compile(r"\r|&gt;|\xa0"),
        "chinese": re.compile(u"[\u4e00-\u9fa5]*"),
        "title": re.compile(r'<title|<h[1-3].*'),
        "date": re.compile(
            r'(20)?([0-1]\d(' + u'\u5e74' + '|\s|Y|/|-)?(1[0-2]|0?1-9).(3[0-1]|2\d|1\d|0?\d)(' + u'\u65e5' + '|d|\s)?((([0-1]\d|2[0-4])[:' + u'\u70b9' + 'Hh])?([0-5]\d|0?\d]))?)')
        # "date": re.compile(
        #     r'(20)?([0-1]\d.?[^a-zA-Z\d](1[0-2]|0?\d).?[^a-zA-Z\d](3[0-1]|2\d|1\d|0?\d).?[^a-zA-Z\d/](([0-1]\d|2[0-4]).?[^a-zA-Z\d]([0-5]\d|0?\d]))?)')
        # 时间正则 molly
        # "date": re.compile(r'(20)?([0-1][0-9].?[^a-zA-Z0-9](1[0-2]|0?[0-9])[^a-zA-Z0-9](3[0-1]|2[0-9]|1[0-9]|0?[0-9]).?(([1-2][0-3])|(0?[0-9])+.?([0-5][0-9]|0?[0-9]]))?)')# 时间正则 molly
    }

    def main(self):

        try:
            request = requests.get(url=self.url, params=self.header, timeout=self.timeout)
        except requests.exceptions.Timeout:
            self.elements['state'] = 0
            self.elements['error'] = "ConnectionTimeout"
            return self.elements

        if 'stock.jrj.com.cn' in self.url:
            bsobj = BeautifulSoup(request.text, "lxml")
        else:
            if self.encoding:
                charset = self.encoding
            else:
                charset = chardet.detect(request.content)['encoding']
                if not charset:
                    charset = 'utf8'

            if '.hsmap.com' in self.url:
                request_str = request.text.replace("<span", "<p").replace("</span>", "</p>")
                bsobj = BeautifulSoup(request_str, "html.parser")
            elif '.ebrun.com'  in self.url:
                request.encoding = 'GBK'
                bsobj = BeautifulSoup(request.text, "html.parser")
            elif '.techweb.com' not in self.url:
                request.encoding = charset
                bsobj = BeautifulSoup(request.text, "lxml")
            else:
                bsobj = BeautifulSoup(request.content, "html.parser")

        if 'pedata.cn' in self.url:
            # 清科
            body = bsobj
        elif '.datayuan.cn' in self.url:
            # 数据猿
            body = bsobj.find_all('div', attrs={'class': 'wz-div'})[0]
        elif '.hsmap.com' in self.url:
            # 火石创造
            body = bsobj.find_all('div', attrs={'class': 'detailContent'})[0]
            body = str(body)
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif '.jrj.com.cn' in self.url:
            # 金融界

            body = bsobj.find_all('div', attrs={'class': 'texttit_m1'})[0]
            # body = body.text.encode('utf8')
            # body = "<p>{body_str}</p>".format(body_str=body)
            # body = BeautifulSoup(body, "html.parser")
        elif '.baijingapp.com' in self.url:
            # 白鲸出海
            body = bsobj.find_all('div', attrs={'id': 'message'})[0]
        elif 'luxe.co/' in self.url:
            # 华丽志
            body = bsobj.find_all('div', attrs={'class': 'post-body'})[0]
        elif '.01caijing.com/' in self.url:
            # 01财经
            body = bsobj.find_all('div', attrs={'class': 'article-txt'})[0]
            body = str(body)
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif '.lieyunwang.com/news/' in self.url:
            # 猎云网-快讯
            body = bsobj.find_all('div', attrs={'class': 'main-text mb80'})[0]
            body = str(body)
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif 'technode.com/' in self.url:
            # 动点科技
            body = bsobj.find_all('div', attrs={'class': 'span8 column_container'})[0]

        elif '36dsj.com/' in self.url:
            # 36大数据
            body = bsobj.find_all('div', attrs={'class': 'content'})[0]
            body = str(body)
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif 'ifeng.com/' in self.url:
            # 凤凰财经
            body = bsobj.find_all('div', attrs={'id': 'main_content'})[0]
            body = str(body)
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif 'thepaper.cn' in self.url:
            body = bsobj.find_all('div', attrs={'class': 'news_txt'})[0]
            body = str(body)
            # body = body.replace("<div", "<p").replace("/div>", "/p>")
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif '.chaindd.com' in self.url:
            try:
                from scrapy import Selector
                sel = Selector(request)
                div = sel.xpath("//div[@class='inner']").extract()[0]
                body = BeautifulSoup(div, "html.parser")
            except Exception:
                self.elements['state'] = 0
                self.elements['error'] = "ConnectionTimeout"
                return self.elements
        elif '.528btc.com' in self.url:
            body = bsobj.find_all('div', attrs={'class': 'cbody'})[0]
            body = str(body)
            body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")
        elif 'kuaixun.stcn.' in self.url:
            # 证券时报网-快讯
            body = bsobj.find_all('div', attrs={'id': 'ctrlfscont'})[0]
            body = str(body)
            body = body.replace("<div", "<p").replace("/div>", "/p>")
            # body = "<p>{body_str}</p>".format(body_str=body)
            body = BeautifulSoup(body, "html.parser")

            ad_list = body.find_all('p', attrs={'class': 'adv'})
            for ad_info in ad_list:
                ad_info.extract()
        elif '.rongyu100.' in self.url:
            # 融誉100
            body = bsobj.find_all('div', attrs={'class': 'details'})[0]
            img_list = body.find_all('img')
            body_str = str(body)
            for one_img in img_list:
                body_str = body_str.replace(str(one_img), "<p>"+str(one_img)+"</p>")

            body = BeautifulSoup(body_str, "html.parser")
        elif '.cnbeta.' in self.url:
            body_list = list()
            sum = bsobj.find_all('div', attrs={'class': 'article-summary'})[0].find_all('p')
            art = bsobj.find_all('div', attrs={'id': 'artibody'})[0].find_all('p')
            for one_sum in sum:
                body_list.append(str(one_sum))
            for one_art in art:
                body_list.append(str(one_art))
            body = BeautifulSoup("".join(body_list), "html.parser")
        elif 'iheima.com' in self.url:
            # i黑马
            body = bsobj.find_all('div', attrs={'class': 'main-content'})[0]
            at_list = body.find_all('div', attrs={'class': 'article-list cf'})
            for at_info in at_list:
                at_info.extract()
            dl_list = body.find_all('dl', attrs={'class':'changeshare'})
            for dl_info in dl_list:
                dl_info.extract()

        else:
            if '.jinse.com' in self.url:
                atr_info_list = bsobj.find_all('div', attrs={'class': 'article-info'})
                for atr_info in atr_info_list:
                    atr_info.extract()
            body = bsobj.body
            if not body:
                body = bsobj
        # if 'hsmap.com/' in self.url:
        #
        #     body = body.text.encode('utf8')
        #     body = "<p>{body_str}</p>".format(body_str=body)
        #     body = BeautifulSoup(body, "html.parser")

        alternative_dict = {}

        for tag in body.find_all(True):
            # if tag.name in ("script", "style", "link"):  # 如果是这三个标签之一，删除这个标签
            if tag.name in ("style", "script", "link", "textarea", "input", "select",
                            "frame"):  # 如果是这三个标签之一，删除这个标签 molly # ,"form", "iframe"
                tag.extract()
            if tag.name == "p":  # 如果节点是p标签，找到字符和向上两层节点
                parent_tag = tag.parent
                grandparent_tag = parent_tag.parent
                inner_text = tag.text
                if not parent_tag or len(inner_text) < 20:  # 如果该节点为空或无有价值内容
                    continue
                parent_hash = hash(str(parent_tag))  # 内容太多放不进字典，计算字符串哈希值以取唯一值
                grand_parent_hash = hash(str(grandparent_tag))
                if parent_hash not in alternative_dict:  # 如果该节点内有内容，放入向上两层节点内容和分数
                    alternative_dict[parent_hash] = self._tag_score(parent_tag)
                if grandparent_tag and grand_parent_hash not in alternative_dict:
                    alternative_dict[grand_parent_hash] = self._tag_score(grandparent_tag)
                # 计算此节点分数，以逗号和长度作为参考，并使向上两层递减获得加权分
                content_score = 1
                content_score += inner_text.count(",")
                content_score += inner_text.count(u"，")
                content_score += min(math.floor(len(inner_text) / 100), 3)
                alternative_dict[parent_hash]["score"] += content_score
                if grandparent_tag:
                    alternative_dict[grand_parent_hash]["score"] += content_score / 2

        best_tag = None
        for key in alternative_dict:
            alternative_dict[key]["score"] *= 1 - self._link_score(alternative_dict[key]["tag"])
            if not best_tag or alternative_dict[key]["score"] > best_tag["score"]:
                best_tag = alternative_dict[key]
        if not best_tag:
            self.elements['state'] = 0
            self.elements['error'] = "Couldn't find the optimal node"
            return self.elements
        content_tag = best_tag["tag"]
        # 确定title
        if '36kr.com' not in self.url:
            if not self.title:
                self.title = self._find_title(content_tag)
                if not self.title:
                    self.title = self._get_title_from_tag_list(bsobj.title)
        else:
            self.title = self._find_title(content_tag)
            if not self.title:
                self.title = self._get_title_from_tag_list(bsobj.title)

        # 对最优节点格式清洗
        for tag in content_tag.find_all(True):
            del tag["class"]
            del tag["id"]
            del tag["style"]
            g = tag.recursiveChildGenerator()
            while True:
                try:
                    tag = g.next()
                    if tag is None:
                        break
                    # text node
                    if not isinstance(tag, unicode) and tag is not None:
                        # if tag.name == 'a':
                        #     tag.unwrap()
                        #     del tag['class']
                        #     del tag['id']
                        # elif
                        if tag.name == 'img':
                            img_src = tag.get('src')
                            data_src = tag.get('data-src')
                            if img_src is None and data_src is None:
                                tag.extract()
                            else:
                                if img_src:
                                    img_src = img_src.strip()
                                if data_src:
                                    data_src = data_src.strip()
                                    if data_src.startswith("http") or data_src.startswith("https"):
                                        # 如果data_src是合理的链接, 取data_src的值 molly
                                        img_src = data_src
                                    else:
                                        tag.extract()
                            attr_names = [attr for attr in tag.attrs]
                            for attr in attr_names:
                                del tag[attr]
                            tag['src'] = img_src
                        else:
                            del tag['class']
                            del tag['id']
                        continue
                except StopIteration:
                    break
        # 清理标签，清理无用字段
        content_tag = self._clean(content_tag, "h1")
        content_tag = self._clean(content_tag, "object")
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "form", alternative_dict)
        if len(content_tag.find_all("h2")) == 1:
            content_tag = self._clean(content_tag, "h2")
        content_tag = self._clean(content_tag, "iframe")
        # content_tag = self._clean(content_tag, "script")
        alternative_dict, content_tag = self._find_table(content_tag, alternative_dict)
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "ul", alternative_dict)
        alternative_dict, content_tag = self._clean_alternative_dict(content_tag, "div", alternative_dict)
        # 找寻图片地址
        imgs = content_tag.find_all("img")
        # 得到所有地址，清理无用地址
        for img in imgs:
            src = img.get("src", None)
            if not src:
                img.extract()
                continue
            elif "http://" != src[:7] and "https://" != src[:8]:
                newSrc = urlparse.urljoin(self.url, src)
                newSrcArr = urlparse.urlparse(newSrc)
                newPath = posixpath.normpath(newSrcArr[2])
                newSrc = urlparse.urlunparse((newSrcArr.scheme, newSrcArr.netloc, newPath,
                                              newSrcArr.params, newSrcArr.query, newSrcArr.fragment))
                img["src"] = newSrc
        tables = content_tag.find_all('table')
        table_list = list()
        # for table in tables:
        #     table_list.append(str(table))
        #     table.extract()
        # 正文内中文内容少于设定值，默认定位失败
        content_text = content_tag.get_text(strip=True, separator=self.separator)
        content_length = len("".join(self.regexps["chinese"].findall(content_text)))
        if content_length <= self.shortest_length:
            self.elements['state'] = 0
            self.elements['error'] = "Page is empty or without content"
            return self.elements

        content = self._parameter_correction(content_tag)

        # 特殊处理content
        if 'http://www.ebrun.com/' in self.url:
            try:
                content_list = content.split('<img src="http://imgs.ebrun.com/images/201511/ybfirst.png"/>')
                content = content_list[0]
            except Exception:
                content = ''

        if 'http://cn.technode.com/' in self.url:
            try:
                content_list = content.split(
                    '<img src="http://static.technode.com/wp-content/themes/technode-2013-cn/images/icons/similar-left.png"/>')
                content = content_list[0]
            except Exception:
                content = ''

        # 处理img
        if '.datayuan.cn' in self.url:
            # 数据猿头图
            try:
                post_img = body.find_all('div', attrs={'class': 'wz-div-img'})[0].img.get('src')
                post_img = 'http://www.datayuan.cn%s' % post_img
                if not self.img:
                    self.img = list()
                self.img.insert(0, post_img)
            except Exception:
                traceback.print_exc()
        if 'iyiou.com' in self.url or 'ctoutiao.com' in self.url:
            # 获取亿欧/创投条 头图
            try:
                post_img = body.find_all(attrs={'id': 'post_thumbnail'})[0].img.get('src')
                if not self.img:
                    self.img = list()
                self.img.insert(0, post_img)
            except Exception:
                traceback.print_exc()
        if 'lieyunwang.com' in self.url:
            # 获取猎云网头图
            try:
                one_img = body.find_all(attrs={'class': 'img-fuil img-round'})[0]
                post_img = one_img.get('src')
                self.title = one_img.get('alt')
                if not self.img:
                    self.img = list()
                self.img.insert(0, post_img)
            except Exception:
                traceback.print_exc()
            wx_code_url = 'http://www.lieyunwang.com/img/ly_img_qrcode_weixin.png'
            content = self._remove_content_img(content, wx_code_url)

            c_code_url = 'http://cdnwww.lieyunwang.com/themes/default/images/theme/company_code.jpg'
            while c_code_url in content:
                content = self._remove_content_img(content, c_code_url)

        if 'cheyun.com' in self.url:
            cy_img = 'http://assets.cheyun.com/v2/official/mobile/images/app/onelevel/code.png'
            content = self._remove_content_img(content, cy_img)

        if '.cnbeta.' in self.url:
            cb_img = "https://static.cnbetacdn.com/topics/3ddfd1a057911fd.png"
            cb_img2 = "https://static.cnbetacdn.com/share/r2.gif"
            content = self._remove_content_img(content, cb_img)
            content = self._remove_content_img(content, cb_img2)
        if self.with_date:

            if '.techweb.com' in self.url:
                try:
                    self.date = bsobj.find_all('span', attrs={'class': 'time'})[0].text
                except Exception:
                    self._find_date(content_tag)
            else:
                self._find_date(content_tag)

            try:
                self.date = self.date.encode('utf8')
            except Exception:
                print 'time encoding error'
            #
            # if 'tuoniao.fm' in self.url:
            #     self.date = bsobj.find_all(attrs={'class': 'article-time'})[0].text

            # 处理时间
            if self.date:
                # 36kr
                self.date = self.date.replace('"', '')
                # 2017-12-09 样式
                self.date = self.date.replace('<', '')
                self.date = self.date.replace('>', '')

            self.elements['date'] = self.date

        html_parser = HTMLParser.HTMLParser()

        # self.elements['content'] = html_parser.unescape(content)
        self.elements['content'] = content
        self.elements['img'] = self.img
        # self.elements['title'] = html_parser.unescape(self.title)
        self.elements['title'] = self.title
        self.elements['summary'] = self.summary
        self.elements['tables'] = table_list
        return self.elements

    def _remove_content_img(self, content, img_url):
        if img_url in self.img:
            self.img.remove(img_url)
        img_tag_str = '<img src="{}"/>'.format(img_url)
        content = content.replace(img_tag_str, '')
        return content

    def _tag_score(self, tag):
        """加权框架分计算"""
        score = 0
        if tag.name == "div":
            score += 5
        elif tag.name in ["pre", "td", "blockquote"]:
            score += 3
        elif tag.name in ["address", "ol", "ul", "dl", "dd", "dt", "li", "form"]:
            score -= 3
        elif tag.name in ["h1", "h2", "h3", "h4", "h5", "h6", "th"]:
            score -= 5
        score += self._class_score(tag)
        return {"score": score, "tag": tag}

    def _class_score(self, tag):
        """加权类分计算"""
        score = 0
        if "class" in tag:
            if self.regexps["negative"].search(tag["class"]):
                score -= 25
            elif self.regexps["positive"].search(tag["class"]):
                score += 25
        if "id" in tag:
            if self.regexps["negative"].search(tag["id"]):
                score -= 25
            elif self.regexps["positive"].search(tag["id"]):
                score += 25
        return score

    @staticmethod
    def _link_score(tag):
        """加权标签内部分数"""
        links = tag.find_all("a")
        textLength = len(tag.text)
        if textLength == 0:
            return 0
        link_length = 0
        for link in links:
            link_length += len(link.text)
        return link_length / textLength

    def _clean(self, content, tag):
        """清理符合条件的标签"""
        target_list = content.find_all(tag)
        flag = False
        if tag == "object" or tag == "embed":
            flag = True
        for target in target_list:
            attribute_values = ""
            for attribute in target.attrs:
                get_attr = target.get(attribute[0])
                attribute_values += get_attr if get_attr is not None else ""
            if flag and self.regexps["videos"].search(attribute_values) \
                    and self.regexps["videos"].search(target.encode_contents().decode()):
                continue
            target.extract()
        return content
    def _find_table(self, content,alternative_dict):
        """处理table标签"""
        tags_list = content.find_all('table')
        for tempTag in tags_list:
            score = self._class_score(tempTag)
            hash_tag = hash(str(tempTag))
            if hash_tag in alternative_dict:
                content_score = alternative_dict[hash_tag]["score"]
            else:
                content_score = 0
            # 清理负分节点
            if score + content_score < 0:
                tempTag.extract()
            else:
                 while tempTag.find_all('a') or tempTag.find_all('span') or tempTag.find_all('ul') or tempTag.find_all('strong') or tempTag.find_all('p') or tempTag.find_all('div')or tempTag.find_all('li'):
                     tempTag = self._clean_table_son(tempTag)

        return alternative_dict, content
    def _clean_table_son(self, content_tag):
        for tag in content_tag.find_all(True):
            del tag["class"]
            del tag["id"]
            del tag["style"]
            g = tag.recursiveChildGenerator()
            while True:
                try:
                    tag = g.next()
                    if tag is None:
                        break
                    # text node
                    if not isinstance(tag, unicode) and tag is not None:
                        if tag.name == 'span' or tag.name == 'ul' or tag.name == 'strong' or tag.name == 'p' or tag.name == 'div' or tag.name == 'li':
                            tag.unwrap()
                            del tag['class']
                            del tag['id']
                        elif tag.name == 'img':
                            img_src = tag.get('src')
                            data_src = tag.get('data-src')
                            if img_src is None and data_src is None:
                                tag.extract()
                            else:
                                if img_src:
                                    img_src = img_src.strip()
                                if data_src:
                                    data_src = data_src.strip()
                                    if data_src.startswith("http") or data_src.startswith("https"):
                                        # 如果data_src是合理的链接, 取data_src的值 molly
                                        img_src = data_src
                                    else:
                                        tag.extract()
                            attr_names = [attr for attr in tag.attrs]
                            for attr in attr_names:
                                del tag[attr]
                            tag['src'] = img_src
                        else:
                            del tag['class']
                            del tag['id']
                        continue
                except StopIteration:
                    break
        return content_tag


    def _clean_alternative_dict(self, content, tag, alternative_dict):
        """字典计分加权以清理无用字段"""
        tags_list = content.find_all(tag)
        # 对每一节点评分并调用存档评分
        for tempTag in tags_list:
            score = self._class_score(tempTag)
            hash_tag = hash(str(tempTag))
            if hash_tag in alternative_dict:
                content_score = alternative_dict[hash_tag]["score"]
            else:
                content_score = 0
            # 清理负分节点
            if score + content_score < 0:
                tempTag.extract()
            else:
                p = len(tempTag.find_all("p"))
                img = len(tempTag.find_all("img"))
                li = len(tempTag.find_all("li")) - 100
                input_html = len(tempTag.find_all("input_html"))
                embed_count = 0
                embeds = tempTag.find_all("embed")
                # 如果找到视频，考虑删除节点
                for embed in embeds:
                    if not self.regexps["videos"].search(embed["src"]):
                        embed_count += 1
                linkscore = self._link_score(tempTag)
                contentLength = len(tempTag.text)
                toRemove = False
                # 删除节点逻辑
                if img > p:
                    # toRemove = True
                    if p > 0:
                        toRemove = True
                    else:
                        # div 中没有 p 元素
                        toRemove = False
                        img_list = tempTag.find_all("img")
                        for img_tag in img_list:
                            toRemove = False
                            src = img_tag.get('src')
                            if "http://" != src[:7] and "https://" != src[:8]:
                                toRemove = True
                                # img_tag.extract()
                                break
                elif li > p and tag != "ul" and tag != "ol":
                    toRemove = True
                elif input_html > math.floor(p / 3):
                    toRemove = True
                elif contentLength < 25 and (img == 0 or img > 2):
                    toRemove = True
                elif score < 25 and linkscore > 0.2:
                    toRemove = True
                elif score >= 25 and linkscore > 0.5:
                    toRemove = True
                elif (embed_count == 1 and contentLength < 35) or embed_count > 1:
                    toRemove = True
                # 逻辑成立则删除节点
                if toRemove:
                    tempTag.extract()
        return alternative_dict, content

    def _parameter_correction(self, content):
        """依据选择参数的调整格式"""
        content_tag_list = []
        for tag in content:
            if not isinstance(tag, bs4.element.Tag):
                continue
            # if tag.name == 'table' or tag.name == 'tbody' or tag.name == 'th' or tag.name == 'td':
            #     continue
            if "<img" in tag.decode():
                content_tag_list.extend(tag.find_all("img"))

                p_tag = "<p>{text}</p>".format(text=tag.text.encode('utf8'))
                p_tag = BeautifulSoup(p_tag, "html.parser")
                p_tag = p_tag.find_all(True)[0]
                content_tag_list.append(p_tag)
            else:
                content_tag_list.append(tag)
        self.img = [tag.get("src") for tag in content_tag_list if tag.name == "img"]
        # 对于各种参数的选择，原地清理列表并筛选列表
        if not self.word_with_format:
            for v in range(len(content_tag_list)):
                if isinstance(content_tag_list[v], bs4.element.Tag):
                    if content_tag_list[v].name == 'img':
                        src = content_tag_list[v].get("src")
                        if not self.keep_gif and ('.gif' in src or '.GIF' in src):
                            src = None
                        if self.img_with_format and src:
                            src = '<img src="' + src + '"/>'
                        content_tag_list[v] = src
                    elif content_tag_list[v].name == 'a' or content_tag_list[v].name == 'table':
                        # content_tag_list[v] = src
                        continue
                    else:
                        if isinstance(content_tag_list[v], bs4.element.NavigableString):
                            content_tag_list[v] = content_tag_list[v].string
                        content_tag_list[v] = content_tag_list[v].get_text(strip=True)
                        content_tag_list[v] = self.regexps["symbol"].sub("", content_tag_list[v])
                        if len("".join(self.regexps["chinese"].findall(content_tag_list[v]))) < self.smallest_length:
                            content_tag_list[v] = None  # 清理每段低于最小长度的文字节点
        content_tag_list = filter(lambda x: x, content_tag_list)
        content_tag_list = list(map(lambda x: str(x.encode('utf8')), content_tag_list))
        content = self.separator.join(content_tag_list)

        return content

    def _find_title(self, content_tag):
        """由正文节点向前寻找标题（h1-h3)"""
        previous = content_tag.find_all_previous()
        for brother_tag in previous:
            if brother_tag.name in ["h1", "h2", "h3"]:  # 只提取这些元素中的text作为title molly

                # 过滤换行和制表符
                title_str = str(brother_tag)
                title_str = title_str.replace('\r', '')
                title_str = title_str.replace('\n', '')
                title_str = title_str.replace('\t', '')
                title_list = self.regexps["title"].findall(title_str)
                if title_list:
                    title = self.regexps['brackets'].sub("", title_list[0])
                    title = title.strip()
                    if title:
                        return title
        return None

    def _get_title_from_tag_list(self, title_tag):
        try:
            title_str = str(title_tag.text.encode('utf8'))
            title_str = title_str.replace('\r', '')
            title_str = title_str.replace('\n', '')
            title_str = title_str.replace('\t', '')
            title_str = title_str.strip()
            return title_str
        except Exception:
            return None

    def _find_date(self, content_tag):
        """由正文节点向前寻找时间
        注意，此模块尚未完善，谨慎使用！
        这个比较麻烦，一方面网上流传的正则表达式很多都无法使用，另一方面不同模板的日期格式各有不同，逻辑往往是互斥的
        因此在简单正则逻辑的基础上，加入投票的概念，当然，有可靠的日期正则也请发给我"""
        """时间正则 molly修改"""
        date_list = []
        previous = content_tag.find_all_previous()

        for brother_tag in previous:
            img_list = brother_tag.find_all('img')
            for one_img in img_list:
                one_img.extract()
            # a_list = brother_tag.find_all('a')
            # for one_a in a_list:
            #     one_a.extract()
            # if brother_tag.name == 'img':
            #     continue

            # date_str = str(brother_tag)
            try:
                date_str = str(brother_tag).decode('utf8')
            except Exception:
                date_str = str(brother_tag)

            date_str = date_str.strip()
            date_str = date_str.replace('\r', '')
            date_str = date_str.replace('\t', '')
            date_str = date_str.replace('\n', '')
            date = self.regexps["date"].search(date_str)
            if date:
                date_list.append(date.group().strip())
        if date_list:
            temp_list = list()
            for one_date in date_list:
                one_date = one_date.strip()
                one_date = one_date.replace('\r', '')
                one_date = one_date.replace('\t', '')
                one_date = one_date.replace('\n', '')
                temp_list.append(one_date)
            temp_list = [[x, temp_list.count(x)] for x in temp_list]
            temp_list.sort(key=lambda x: x[1], reverse=True)
            self.date = temp_list[0][0]

    def _kr36_new_content(self, bsobj):
        """特殊处理 36 kr"""
        contain = ''
        try:
            data = re.findall('<script>var props=(.*)</script>', bsobj)[0]
            time1 = re.findall('"published_at":(.*)', data)[0]
            time2 = re.findall(',(.*)', time1)[0]
            published_at = time1[:len(time1) - len(time2) - 1]
            self.date = published_at
            content = re.findall('"title":(.*)</p>(</li></ul>)?","cover"', data)[0]
            content = ''.join(content)
            title = re.findall('(.*),"catch_title":', content)[0]
            self.title = title
            summary = re.findall('"summary":(.*),"content":', content)[0]
            self.summary = summary
            contain = re.findall('"content":"(.*)', content)[0].replace('\\', '') + '</p>'

        except Exception as e:
            print(e)
        return contain



# 示例
if __name__ == "__main__":

    url = r"http://kuaixun.stcn.com/2018/0410/14100438.shtml"
    task = EYE(url=url, with_date=True)
    data = task.main()

    # 如果图片没有, 追加<img> 到content前面 molly
    # 如果图片链接有, 直接替换 molly

    print 'ok\n'
    # print data



