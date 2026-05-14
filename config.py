"""CNKI 论文助手配置模块"""

# ===================== API 端点 =====================
IP_LOGIN_API = "https://login.cnki.net/TopLoginCore/api/loginapi/IpLoginPo"
TARGET_API = "https://kns.cnki.net/kns8s/brief/grid"
DETAIL_PAGE_BASE = "https://kns.cnki.net/kns8s/defaultresult/index"
PDF_DOWNLOAD_BASE = "https://bar.cnki.net/bar/download/order"

# ===================== 默认请求头 =====================
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Referer": "https://kns.cnki.net",
    "Origin": "https://kns.cnki.net",
    "Content-Type": "application/json; charset=UTF-8",
}

SEARCH_HEADERS = {
    "User-Agent": DEFAULT_HEADERS["User-Agent"],
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://kns.cnki.net",
    "Referer": "https://kns.cnki.net/kns8s/AdvSearch",
    "X-Requested-With": "XMLHttpRequest",
}

# ===================== 默认查询参数 =====================
# 基于期刊来源检索的请求体模板
JOURNAL_PAYLOAD = {
    "boolSearch": "true",
    "QueryJson": '',
    "pageNum": "1",
    "pageSize": "20",
    "dstyle": "listmode",
    "boolSortSearch": "false",
    "sentenceSearch":"false",
    "productStr": "YSTT4HG0,LSTPFY1C,RMJLXHZ3,JQIRZIYA,JUP3MUPD,1UR4K4HZ,BPBAFJ5S,R79MZMCB,MPMFIG1A,EMRPGLPA,J708GVCE,ML4DRIDX,WQ0UVIAA,NB3BWEHK,XVLO76FD,HR1YT1Z9,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R,",
    "aside": "",
    "searchFrom": "资源范围：总库;  时间范围：更新时间：不限;",
    "subject": "",
    # "turnpage": "8Kf6r96aVUubfe4hUZXU-w!!",
    "language": "",
    "uniplatform": "",
    "CurPage": "1"
}
JOURNAL_QUERY = {
    "Platform": "",
    "Resource": "CROSSDB",
    "Classid": "WD0FTY92",
    "Products": "",
    "QNode": {
        "QGroup": [
            {
                "Key": "Subject",
                "Title": "",
                "Logic": 0,
                # "Items": [{
                #     "Field": "LY",
                #     "Value": "",
                #     "Operator": "DEFAULT",
                #     "Logic": 0,
                #     "Title": "文献来源"
                # }]
                "Items":[],
                "ChildItems":[
                    {
                        "Key":"input[data-tipid=gradetxt-1]",
                        "Title":"文献来源",
                        "Logic": 0,
                        "Items":[
                            {
                                "Key":"input[data-tipid=gradetxt-1]",
                                "Title":"文献来源",
                                "Logic": 0,
                                "Field": "LY",
                                "Operator": "DEFAULT",
                                "Value": "",
                                "Value2": "",
                            }
                        ],
                        "ChildItems":[]
                    }
                ]
            },
            {
                "Key": "ControlGroup",
                "Title": "",
                "Logic": 0,
                "Items": [],
                "ChildItems": []
            } 
        ]
    },
    "ExScope": "1",
    "SearchType": 1,
    "Rlang": "BOTH",
    "KuaKuCode": "YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A,EMRPGLPA,WQ0UVIAA,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R",
    "Expands": {},
    "View": "changeDBCh",
    "SearchFrom": 1
}
# 基于文献标题精准检索的请求体模板
TITLE_PAYLOAD = {
    "boolSearch": "true",
    "QueryJson": '{"Platform":"","Resource":"CROSSDB","Classid":"WD0FTY92","Products":"","QNode":{"QGroup":[{"Key":"Subject","Title":"","Logic":0,"Items":[{"Field":"TI","Value":"","Operator":"TOPRANK","Logic":0,"Title":"篇名"}]}]},"ExScope":1,"SearchType":2,"Rlang":"BOTH","KuaKuCode":"YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A,EMRPGLPA,WQ0UVIAA,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R","Expands":{},"SearchFrom":1}',
    "pageNum": "1",
    "pageSize": "20",
    "dstyle": "listmode",
    "boolSortSearch": "false",
    "sentenceSearch":"false",
    "productStr": "YSTT4HG0,LSTPFY1C,RMJLXHZ3,JQIRZIYA,JUP3MUPD,1UR4K4HZ,BPBAFJ5S,R79MZMCB,MPMFIG1A,EMRPGLPA,J708GVCE,ML4DRIDX,WQ0UVIAA,NB3BWEHK,XVLO76FD,HR1YT1Z9,BLZOG7CK,PWFIRAGL,EMRPGLPA,J708GVCE,ML4DRIDX,NLBO1Z6R,NN3FJMUV,",
    "aside": "",
    "searchFrom": "资源范围：总库;  时间范围：更新时间：不限;",
    "subject": "",
    "turnpage": "8Kf6r96aVUubfe4hUZXU-w!!",
    "language": "",
    "uniplatform": "",
    "CurPage": "1"
}
TITLE_QUERY = {
    "Platform": "",
    "Resource": "CROSSDB",
    "Classid": "WD0FTY92",
    "Products": "",
    "QNode": {
        "QGroup": [{
            "Key": "Subject",
            "Title": "",
            "Logic": 0,
            "Items": [{
                "Field": "TI",
                "Value": "",
                "Operator": "TOPRANK",
                "Logic": 0,
                "Title": "篇名"
            }]
        }]
    },
    "ExScope": 1,
    "SearchType": 2,
    "Rlang": "BOTH",
    "KuaKuCode": "YSTT4HG0,LSTPFY1C,JUP3MUPD,MPMFIG1A,EMRPGLPA,WQ0UVIAA,BLZOG7CK,PWFIRAGL,NN3FJMUV,NLBO1Z6R",
    "Expands": {},
    "SearchFrom": 1
}

# ===================== 超时设置 =====================
LOGIN_TIMEOUT = 15
REQUEST_TIMEOUT = 20
DOWNLOAD_TIMEOUT = 60  # PDF 下载超时时间

# ===================== 输出目录 =====================
OUTPUT_DIR = "output"
