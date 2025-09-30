class ServiceLocator:
    _services = {}

    @classmethod
    def register(cls, service_name, service_instance):
        cls._services[service_name] = service_instance

    @classmethod
    def get(cls, service_name):
        return cls._services.get(service_name)