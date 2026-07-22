try:
    from gwa import models as gwa_models
    from cmi import models as cmi_models
except Exception as e:
    print(f"WARNING lib_djangoapp{e}")

class ConfigurationItemDummy:
    description="Configuration Item Not Found"
    def __init__(self,
                 name=None):
        self.name = name 

def get_cmi(name):
     
    try:
        cmi= cmi_models.ConfigurationItem.objects.get(name=name)
    except Exception as e:
        cmi=ConfigurationItemDummy(name=name)

    return cmi

