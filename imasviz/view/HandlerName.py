class HandlerName:
    def __init__(self):
        pass

    @staticmethod
    def getAPIHandler(handlerValue):
        return "api_" + str(handlerValue)

    @staticmethod
    def getWxDataTreeViewHandler(handlerValue):
        return "dtv_" + str(handlerValue)

    @staticmethod
    def getDataSourceHandler(handlerValue):
        return "ds_" + str(handlerValue)

    @staticmethod
    def getDataSourceFactoryHandler(handlerValue):
        return "dsf_" + str(handlerValue)

    @staticmethod
    def getContextHandler(handlerValue):
        return "ctx_" + str(handlerValue)

