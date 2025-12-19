import json

def get_form_json_template():
    """生成指定的 JSON 对象（Python 字典）"""
    # 构建完整的配置字典
    form_json_template = {
        "list": [],
        "config": {
            "labelWidth": 100,
            "labelPosition": "right",
            "size": "small",
            "customClass": "",
            "ui": "element",
            "layout": "horizontal",
            "labelCol": 3,
            "width": "100%",
            "hideLabel": False,
            "hideErrorMessage": False,
            "formRules": [],
            "mobileInitialScale": 1,
            "mobileMinScale": 1,
            "mobileMaxScale": 1,
            "eventScript": [
                {"key": "mounted", "name": "mounted", "func": ""},
                {"key": "refresh", "name": "refresh", "func": ""},
                {"key": "beforeSave", "name": "beforeSave", "func": ""},
                {"key": "afterSave", "name": "afterSave", "func": ""},
                {"key": "afterEditSave", "name": "afterEditSave", "func": ""}
            ],
            "styleSheets": ".水平居中{\n  text-align:center;\n}\n.垂直居中{\n  margin-top:9px !important;\n  margin-bottom:9px !important;\n}\n.标签标红 .el-form-item__label{\n  color:red;\n}\n.标签加粗 .el-form-item__label{\n  font-weight:bold \n}\n.标签变细 .el-form-item__label{\n  font-weight:normal !important;;\n}\n.标签斜体 .el-form-item__label{\n  font-style: italic;\n}\n.文字标红 .el-form-item__content{\n  color:red;\n}\n.文字加粗 .el-form-item__content{\n  font-weight:bold \n}\n.文字放大 .el-form-item__content{\n  font-size:24px; \n}\n.文字变细 .el-form-item__content{\n  font-weight:normal !important\n}\n.输入框标红 .el-input__inner{\n  color:red;\n  -webkit-text-fill-color: red !important; //修改输入框文字颜色\n}\n.输入框加粗 .el-input__inner{\n  font-weight:bold;\n}\n.输入框变细 .el-input__inner{\n  font-weight:normal;\n}\n.输入框斜体 .el-input__inner{\n  font-style: italic;\n}\n.多选框文字标红 .el-checkbox__label{\n  color:red;\n}\n.多选框文字加粗 .el-checkbox__label{\n  font-weight:bold;\n}\n.单选框文字标红 .el-radio__label{\n  color:red;\n}\n.单选框文字加粗 .el-radio__label{\n  font-weight:bold;\n}\n.单行框禁用样式 .el-form-item__content .el-input.is-disabled .el-input__inner{\n  background-color:unset;\n  border:unset;\n  color:rgba(0,0,0,.8);\n  padding:0;\n}\n.移动端子表单间隔缩小 .form-table-mobile-item .el-form-item.el-form-item--small{\n  margin-bottom:3px;\n}\n.单行框前间距减少 .el-form-item__content .el-input .el-input__inner{\n  padding-left:5px;\n}\n ",
            "actionButtonData": [
                {"eName": "save", "cName": "提交", "enable": True},
                {"eName": "temSave", "cName": "暂存", "enable": False},
                {"eName": "clearDraft", "cName": "清空", "enable": False},
                {"eName": "saveToDraft", "cName": "存为草稿", "enable": False},
                {"eName": "nextBtn", "cName": "新增下一条", "enable": False}
            ],
            "switchAfterSave": False,
            "postServiceList": [],
            "isWatermark": False,
            "watermark": {
                "watermark": "",
                "width": 100,
                "height": 40,
                "rows": 20,
                "cols": 20,
                "x_space": 130,
                "y_space": 200,
                "x": 60,
                "y": 100,
                "color": "#dddddd",
                "alpha": 80,
                "fontsize": 14,
                "loading": False
            },
            "jumpAfterSubmit": False,
            "jumpOptions": {
                "jumpAfterSubmitType": "appPage",
                "appPageType": "form",
                "outsidePageSrc": "",
                "appPageSrc": "",
                "appPageName": ""
            },
            "viewSubmission": False,
            "submitTriggerProcess": False,
            "pcInnerPadding": "0px",
            "pcOutsidePadding": "0px",
            "mobileOutsidePadding": "0px",
            "mobileInnerPadding": "0px"
        }
    }
    return form_json_template


# 如果需要将字典转换为 JSON 字符串，可使用 json 模块


if __name__ == "__main__":
    # 生成 JSON 对象
    result_json = get_form_json_template()

    # 打印结果验证
    print("\n生成的 JSON 字符串：")
    print(result_json)


