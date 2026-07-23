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

def search_object(search:str ):
    dto_list = []
    dto_dict={}
    dto = {'search':search}
    #new_dto = {**dto, 'description': description}
    #results.append(new_dto)
    objs = cmi_models.ConfigurationItem.objects.filter(name__icontains=search)
    dto_dict['ConfigurationItem'] = [
        dto | {'name':obj.name, 
               'description': obj.description} for obj in objs
        ] or [
            dto | {'name':'n/a',
                   'description': 'Not found in ConfigurationItem'}]

    objs = gwa_models.GoogleUser.objects.filter(email__icontains=search)
    dto_dict['GoogleUser'] = [
        dto | {'name':obj.email, 
               'description': obj.ou} for obj in objs
        ] or [
            dto | {'name':'n/a',
                   'description': 'Not found in GoogleUser'}]
    return dto_dict 
    
    #for obj in cmi :
    #    new_dto = dto | {'description': obj.description}
    #    dto_list.append(new_dto)
    
