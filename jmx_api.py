import io
import os
import sys
import subprocess
import time
import json
import logging
from string import Template
import xml.etree.ElementTree as ET
#from lxml import etree as LET



# 通过解析xml文件
'''
try:
    import xml.etree.CElementTree as ET
except:
    import xml.etree.ElementTree as ET

从Python3.3开始ElementTree模块会自动寻找可用的C库来加快速度    
'''


# JMETER_HOME = "/Users/topq/Documents/tools/Java/apache-jmeter-3.0"


# JMETER_HOME = "/Users/topq/Documents/tools/Java/apache-jmeter-4.0"


def load(file, encoding=None):
    '''
        加载jmx脚本，解析成http_runner的json模式
        :param file: 文件url
        :param encoding: 字符编码

        :return: ok or error
        '''
    json_dict = []

    config_data = {}
    config_data['config'] = {}
    test_data = []

    json_dict.append(config_data)

    try:
        tree = ET.parse(file)
        root = tree.getroot()

        # TestPlan name, ConfigTestElement
        get_config_element(root, config_data)
        get_args_element(root.iter("Arguments"), config_data)
        get_test_element(root.iter("HTTPSamplerProxy"), test_data)
        get_assert_element(root.iter("ResponseAssertion"), test_data)

        for test in test_data:
            json_dict.append(test)

        print(json_dict)
        return json_dict
    except:
        print(json_dict)
        print("xx test_data",len(test_data))
        return json_dict


def get_config_element(tree, json_data):
    '''
    解析jmx中的通用配置参数
    '''

    # TestPlan name
    plan = tree.find('./hashTree/TestPlan')
    enabled = plan.get('enabled')
    testname = plan.get('testname')

    if enabled == 'true':
        json_data['config']["name"] = testname + "-config"

    # ConfigTestElement
    base_url = ""
    protocol = ""
    port = ""

    for configNode in tree.iter('ConfigTestElement'):
        if configNode.get("enabled") == 'true':
            # print (",,",neighbor.attrib)
            for prop in configNode:  # 查询HTTPSampler节点子节点

                if prop.get("name") == 'HTTPSampler.protocol':
                    protocol = prop.text + "://" if prop.text else ""

                elif prop.get("name") == 'HTTPSampler.domain':
                    base_url = prop.text if prop.text else ""

                elif prop.get("name") == 'HTTPSampler.port':
                    port = ":" + prop.text if prop.text else ""

    json_data['config']["request"] = {}
    json_data['config']["request"]["base_url"] = protocol + base_url + port

    # HeaderManager
    json_data['config']["request"]["headers"] = {}
    header = {}
    header_name = ""
    header_value = ""
    for headerNode in tree.iter('HeaderManager'):
        if headerNode.get("enabled") == 'true':
            print(",,", headerNode.attrib)
            for prop in headerNode.iter("stringProp"):  # 查询stringProp节点子节点

                if prop.get("name") == 'Header.name':
                    header_name = prop.text

                elif prop.get("name") == 'Header.value':
                    header_value = prop.text

    header[header_name] = header_value;
    json_data['config']["request"]["headers"] = header


def get_args_element(tree, json_data):
    '''
    解析jmx中的通用参数用例
    '''

    tests = []
    for args in tree:
        if args.get("enabled") == 'true':
            test = {}
            test["name"] = args.get("testname")
            test["variables"] = []

            args_name = ""
            args_value = ""
            for elementProp in args.iter("elementProp"):
                variable = {}
                args_name = elementProp.get('name')
                args_value = elementProp.find("./stringProp[@name='Argument.value']").text
                variable[args_name] = args_value

                test["variables"].append(variable)

            # tests.append(test)
            json_data["config"]["variables"] = test["variables"]



def get_test_element(tree, json_data):
    '''
    解析jmx中的通用测试用例
    '''
    print ("get_test_element")

    # tests = []
    for args in tree:
        if args.get("enabled") == 'true':
            test = {}
            test['test'] = {}
            test['test']["name"] = args.get("testname")

            # 请求接口地址等信息
            request = {}
            test['test']["request"] = request
            request['url'] = args.find("./stringProp[@name='HTTPSampler.path']").text
            request['method'] = args.find("./stringProp[@name='HTTPSampler.method']").text

            print(request['url'])

            # 请求参数解析
            params = {}
            args_name = ""
            args_value = ""

            elementProp_list = args.findall("./elementProp/collectionProp/elementProp")
            for elementProp in elementProp_list:
                if 'elementProp' in elementProp.tag:
                    args_name = elementProp.get('name')
                    args_value = elementProp.find("./stringProp[@name='Argument.value']").text
                    params[args_name] = args_value

            request["params"] = params
            json_data.append(test)
            print("json_data", len(json_data))



def get_assert_element(tree, json_data):
    '''
    解析jmx中的断言及正则测试用例
    '''
    print ("get_assert_element")

    validate_list = []

    for args in tree:
        if args.get("enabled") == 'true':

            # 获取断言

            elementProp_list = args.findall("./collectionProp/stringProp")
            for elementProp in elementProp_list:
                # 此处只能是stringProp
                if 'stringProp' in elementProp.tag:
                    text = '{' + elementProp.text.replace("&quot;", '"') + '}'
                    #print(text)
                    if text.find(":") < 0:
                        print("not json---")
                        continue

                    assert_test = {}
                    assert_list = []
                    extract = []
                    try:
                        tmp_obj = json.loads(text)
                        #print(tmp_obj)
                    except:
                        print("json.loads error,continue---",text)
                        continue

                    if tmp_obj is None:
                        print("continue---")
                        continue

                    # 遍历属性，添加到断言列表
                    for key in tmp_obj.keys():
                        assert_test["eq"] = [key, tmp_obj.get(key)]
                        assert_list.append(assert_test)
                        # 判断是否要走正则提取
                        if key not in ["status_code", "headers.Content-Type"]:
                            extract_obj = {}
                            extract_obj[key] = 'content.' + key
                            extract.append(extract_obj)

                            # 断言中也同步调整
                            assert_test["eq"] = ['$' + key, tmp_obj.get(key)]

                    # 属性遍历完毕，进行数据整合
                    # 将断言补充到对应test的validate中
                    validate_size = len(validate_list)
                    if validate_size >= 0:

                        if len(json_data) > validate_size:
                            tmp_list = []
                            tmp_list = assert_list.copy()
                            json_data[validate_size]['test']["validate"] = tmp_list

                            # 补充正则提取 --可能部分规则需要手动修正
                            tmp_list2 = []
                            tmp_list2 = extract.copy()
                            json_data[validate_size]['test']['extract'] = tmp_list2

                        validate_list.append(0)



def getDateTime():
    '''
    获取当前日期时间，格式'20150708085159'
    '''
    return time.strftime(r'%Y%m%d%H%M%S', time.localtime(time.time()))


def execcmd(command):
    print(f"command={command}")

    output = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
        universal_newlines=True)

    stderrinfo, stdoutinfo = output.communicate()
    print(f"stderrinfo={stderrinfo}")
    print(f"stdoutinfo={stdoutinfo}")
    print("returncode={0}".format(output.returncode))
    return output.returncode


def generate_report_path():
    '''
    生成jmx脚本运行需要的数据和报告文件路径，格式'20150708085159'
    '''
    now = getDateTime()
    curr_path = os.path.join(sys.path[0], "static", "jmeter_reports")
    if not os.path.exists(curr_path):
        os.makedirs(curr_path)

    csvfilename = os.path.join(curr_path, "result{0}.csv".format(now))
    htmlreportpath = os.path.join(curr_path, "htmlreport{0}".format(now))
    reportname = "jmeter-htmlreport{0}".format(now)
    if not os.path.exists(htmlreportpath):
        os.makedirs(htmlreportpath)


    return csvfilename,htmlreportpath,reportname


def execjmx(jmx_file_path, Num_Threads, Loops):
    tmpstr = ''
    with open(jmx_file_path, "r", encoding="utf-8") as file:
        tmpstr = Template(file.read()).safe_substitute(
            num_threads=Num_Threads,
            loops=Loops
        )

    #调用命令，生成jmx脚本执行的数据与报告生成文件路径
    (csvfilename, htmlreportpath, reportname) = generate_report_path()


    #此处逻辑移植到generate_report_path方法实现
    # now = getDateTime()
    # curr_path = os.path.join(sys.path[0], "jmeter_reports")
    #
    # if not os.path.exists(curr_path):
    #     os.makedirs(curr_path)
    #
    # csvfilename = os.path.join(curr_path, "result{0}.csv".format(now))
    # htmlreportpath = os.path.join(curr_path, "htmlreport{0}".format(now))
    # if not os.path.exists(htmlreportpath):
    #     os.makedirs(htmlreportpath)
    # reportname = "jmeter-htmlreport{0}".format(now)
    # logger.info("reportname={0}".format(reportname))

    execjmxouthtml = f"{JMETER_HOME}/bin/jmeter.sh -n -t {jmx_file_path} -l {csvfilename} -e -o {htmlreportpath}"
    returncode = execcmd(execjmxouthtml)

    #执行成功，返回数据文件及报告的路径;否则返回错误码
    if returncode == 0:
        return returncode, csvfilename, htmlreportpath,reportname
    else:
        return returncode,'','',''


#
# def read_xml_string(path):
#     '''
#     读取XML文件内容,使用LXML
#     :param path: 文件路径
#
#     :return: content
#     '''
#
#     tree = LET.parse(path)
#     result = LET.tostring(tree, pretty_print=True)
#
#     return result

def indent(elem, level=0):
    i = "\n" + level * "\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def prettyXml(element, indent, newline, level = 0): # elemnt为传进来的Elment类，参数indent用于缩进，newline用于换行
    if element:  # 判断element是否有子元素
        if element.text == None or element.text.isspace(): # 如果element的text没有内容
            element.text = newline + indent * (level + 1)
        else:
            element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * (level + 1)
    #else:  # 此处两行如果把注释去掉，Element的text也会另起一行
        #element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * level
    temp = list(element) # 将elemnt转成list
    for subelement in temp:
        if temp.index(subelement) < (len(temp) - 1): # 如果不是list的最后一个元素，说明下一个行是同级别元素的起始，缩进应一致
            subelement.tail = newline + indent * (level + 1)
        else:  # 如果是list的最后一个元素， 说明下一行是母元素的结束，缩进应该少一个
            subelement.tail = newline + indent * level
        prettyXml(subelement, indent, newline, level = level + 1) # 对子元素进行递归操作


if __name__ == '__main__':
    load('/Users/topq/Documents/ff.jmx', 'utf-8')
    # execjmx('/Users/topq/Documents/sdk-svr-login_2.jmx',1,1)
