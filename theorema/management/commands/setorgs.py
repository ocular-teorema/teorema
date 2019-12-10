from django.core.management.base import BaseCommand
from theorema.orgs.models import Organization
from theorema.cameras.models import Server, Storage

DEFAULT_ORG_NAME = 'Ocular'
DEFAULT_ADDRESS = '0.0.0.0'
DEFAULT_STORAGE_NAME = 'default'
DEFAULT_STORAGE_PATH = '/home_VideoArchive'


class Command(BaseCommand):

    def handle(self, *args, **options):

        org_name = input("Name of organization (default - Ocular): ")
        if not org_name:
            org_name = DEFAULT_ORG_NAME

        address = input('Specify IP address (default = 0.0.0.0): ')
        if not address:
            address = DEFAULT_ADDRESS
        local_address = input('Specify local IP address (default = 0.0.0.0): ')
        if not local_address:
            local_address = DEFAULT_ADDRESS

        server_id = input("Specify MAC-address (required): ")
        if not server_id:
            print('No MAC address specified')
            return
        server_id = str(server_id).upper().replace(':', "")
        server_name = server_id

        existing_org = Organization.objects.all().first()
        if existing_org:
            existing_org.name = org_name
            org = existing_org
        else:
            org = Organization(name=str(org_name))

        existing_server = Server.objects.all().first()
        if existing_server:
            existing_server.name = server_name
            existing_server.address = address
            existing_server.local_address = local_address
            existing_server.organization = org
            existing_server.mac_address = server_id

            server = existing_server
        else:
            server = Server(
                name=server_name,
                address=address,
                local_address=local_address,
                organization=org,
                mac_address=server_id
            )

        existing_storage = Storage.objects.all().first()
        if existing_storage:
            existing_storage.name = DEFAULT_STORAGE_NAME
            existing_storage.path = DEFAULT_STORAGE_PATH

            storage = existing_storage
        else:
            storage = Storage(name=DEFAULT_STORAGE_NAME, path=DEFAULT_STORAGE_PATH)

        org.save()
        server.save()
        storage.save()

        print('Settings saved', flush=True)
