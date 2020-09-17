#-*- coding:utf-8 -*-
__author__ = 'Will'
__data__ = ' 3:29 PM'
import json
import os
import re

def get_target_value(key, dic, tmp_list):
    """

    :param key: 传值要获得值得key
    :param dic: 要解析的字典
    :param tmp_list: 返回给值得list
    :return:
    """

    if not isinstance(dic, dict) or not isinstance(tmp_list, list):
        return 'false argv '

    if key in dic.keys():
        tmp_list.append(dic[key])
    else:
        for value in dic.values():
            if isinstance(value, dict):
                get_target_value(key, value, tmp_list)
            elif isinstance(value, (list, tuple)):
                get_value(key, value, tmp_list)
    return tmp_list


def get_value(key, val, tmp_list):
    for val_ in val:
        if isinstance(val_, dict):
            get_target_value(key, val_, tmp_list)
        elif isinstance(val_, (list, tuple)):
            get_value(key, val_, tmp_list)



#def swagger2json():
def swagger2json(source_file, output_file):
    #写入文件逻辑
    try:
        swagger = json.load(open(source_file, encoding='utf-8'))
    except:
        print("json.load error={0}".format(source_file))
        return -1
        pass
    #swagger = json.load(open("/Users/will/Downloads/swagger_all.json", encoding='utf-8'))
    #获取config字典的参数
    baseurl_val = swagger.get('host')
    name_val = swagger.get('info').get('title')
    config = {
        "name": name_val + '-config',
        "variables": {},
        "request":{
            "base_url": baseurl_val
        }
    }
    swagger_result = []
    swagger_result.append({"config": config})
    path_val = swagger.get('paths')
    #print(path_val)
    #获取test字典内相关的参数
    for u_val in path_val.keys():
        url_val = u_val
        urlpath_val = path_val.get(url_val)
        for m_val in urlpath_val.keys():
            method_val = m_val
            #print(url_val,method_val)
            #print(method_val)
            header_val = urlpath_val.get(method_val).get('produces')
            params_val = urlpath_val.get(method_val).get('parameters')
            name_val = urlpath_val.get(method_val).get('operationId')
            #print(url_val, method_val,name_val, params_val)

            #params_val是具体参数集合，在此参数集合下根据不同的条件获取参数
            for e in params_val:
                #for keys,values  in e.items():
                    # if keys == "name":
                    #     parm = e[keys]
                    #     parms = {}
                    #     # print(parm)
                    #
                    #     parms[parm] = "name1"
                #v = e.get('name')
                #for values in e.values():
                    #当名称是body取ref得关键词，用get_parm方法取值
                    if e['name'] =="body":
                        re_value = get_target_value('$ref',e,[])

                        #re_value = str(re_value)
                        #print(re_value)
                        re_value = re_value[0]
                        key_word = re_value.split('/')[-1]
                        parms_dic = get_definition_parms(swagger, key_word)
                        print(parms_dic)
                    elif e['type'] == "array":
                        re_value1 = get_target_value('items',e,[])
                        if any(re_value1) is True:
                            re_value1 = e.get('items').get("enum")
                        name_key = e['name']
                        parms_dic = {name_key:re_value1}
                        #print(parms_dic)
                    elif e['in'] == "path":
                        name_key = e.get("name")
                        re_value = name_key
                        parms_dic = {name_key:re_value}
                        #print(parms_dic)


                        # parm = e[keys]
                        # parms = {}
                        # # print(parm)
                        #
                        # parms[parm] = "name1"



            request = {
                "params": parms_dic,
                "url": url_val,
                "method": method_val,
                "headers": header_val
            }

            test = {
                "name": name_val,
                "request": request,
                "validate": [
                        {
                            "eq": [
                                "status_code",
                                200
                                ]
                        }
                    ]
                }

            swagger_result.append({"test": test})

        #print(swagger_result)
    #return swagger_result
    #复制到目标
    try:
        with open(output_file, 'w', encoding='utf8') as f:
            json.dump(swagger_result, f, indent=4, separators=(',', ': '), ensure_ascii=False)
    except:
        print("json.dump={0}".format(output_file))
        return -1
        pass

    return 0

def get_definition_parms(swagger, key_word):
    defintions = swagger.get("definitions")
    #print(defintions)
    parms_list = []
    for ref_key,ref_val in defintions.items():
        if ref_key == key_word:    # 等于"$ref": "#/definitions/Pet" 对等
            ref_parm = ref_val
            parm_properties = ref_parm.get("properties")
            #print(parm_properties)
            for r in parm_properties.keys():
                parms_list.append(r)
            #print(parms_list)
            parms_dic = dict(zip(parms_list,parms_list))
            for value in parm_properties.values():
                ref2_val = value
                for keys_ref2,values_ref2 in ref2_val.items():
                    if keys_ref2 == "$ref":
                        defintion_vel = values_ref2
                        defintion_vel = defintion_vel.split('/')[-1]
                        #print(ref_parm)
                        for key_2,value_2 in defintions.items():
                            if key_2 == defintion_vel:
                                #print(defintion_vel)
                                values_ref3 = value_2
                                #print(values_ref3)
                                ref_properties = values_ref3.get("properties")
                                ref_val_list = []
                                for keys_ref_properties in ref_properties.keys():
                                    ref_val_list.append(keys_ref_properties)
                                    #print(ref_val_list)
                                    ref_val_dic = dict(zip(ref_val_list,ref_val_list))
                                    #print(ref_val_dic)
                                    #print(ref2_val)
                        #更新有ref的值
                        defintion_vel = defintion_vel.lower()
                        parms_dic[defintion_vel] = ref_val_dic



                        #print(defintion_vel)
            #     #print(ref2_val)
            # for r in parm_properties.keys():
            #     parms_list.append(r)
            # #print(parms_list)
            # parms_dic = dict(zip(parms_list,parms_list))
            # for tag_key,tag_value in parms_dic.items():
            #     if tag_key == "tags":



                        #print(parms_dic)




    return parms_dic



if __name__ == '__main__':
    swagger2json("/Users/will/Downloads/fate-shoppurchase-api.json", "/Users/will/unit_swagger_back.json")


