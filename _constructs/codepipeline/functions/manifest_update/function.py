import shutil
import json
import yaml
import boto3
from aws_lambda_powertools import Logger
from dulwich import porcelain

logger = Logger()
code_pipeline_client = boto3.client('codepipeline')
secrets_manager_client = boto3.client('secretsmanager')


class Git:
    def __init__(self,
                 cd_repository: str,
                 branch: str,
                 local_repo_path: str,  # 'current path' + '/tmp/repo'
                 target_manifest: str,  # 'deployment.yaml'
                 github_personal_access_token: str):

        self._cd_repository = cd_repository
        self._target_manifest = target_manifest
        self._branch = branch
        self._local_repo_path = local_repo_path
        self._github_personal_access_token = github_personal_access_token
        self._local_repo = None
        self.author = 'aws-codepipeline-lambda <lambda@example.com>'
        self.username = 'not relevant'

    def clone(self):
        logger.info('GitHub CD Repository clone(): '
                    f'source={self._cd_repository}'
                    f'branch={self._branch}'
                    f'target={self._local_repo_path}')
        self._local_repo = porcelain.clone(
            source=self._cd_repository,
            branch=self._branch.encode('utf-8'),  # todo: dev, stg, prd
            password=self._github_personal_access_token,
            username=self.username,
            target=self._local_repo_path,
            checkout=True
        )

    def add(self):
        logger.info(
            f'git add(): repo={self._local_repo}, '
            f'paths={self._local_repo_path + self._target_manifest}')
        porcelain.add(
            repo=self._local_repo,
            paths=self._local_repo_path + self._target_manifest
        )

    def commit(self):
        logger.info(
            f'git commit(): repo={self._local_repo}')
        porcelain.commit(
            repo=self._local_repo,
            message='Update Image Tag',
            author=self.author
        )

    def push(self):
        logger.info(
            f'git push():'
            f'repo={self._local_repo}'
            f'remote_location={self._cd_repository}'
            f'refspecs={self._branch}')

        porcelain.push(
            repo=self._local_repo,
            remote_location=self._cd_repository,
            refspecs=self._branch.encode('utf-8'),
            password=self._github_personal_access_token,
            username=self.username
        )


class ManifestUpdated:
    def __init__(self, target_manifest, container_image_tag):
        self.target_manifest = target_manifest
        self.container_image_tag = container_image_tag

    def update_image_tag(self):
        logger.info('ManifestUpdated update_image_tag()')
        # read manifest
        with open(self.target_manifest, 'r', encoding='utf-8') as f:
            logger.info('ManifestUpdated open(r)')
            manifest = yaml.safe_load(f)
            replaced_manifest = self.replace_image_tag(  # update manifest
                manifest,
                container_image_tag=self.container_image_tag)

        # write manifest
        with open(self.target_manifest, 'w', encoding='utf-8') as f:
            logger.info('ManifestUpdated open(w)')
            yaml.dump(
                data=replaced_manifest,
                stream=f,
                sort_keys=False)  # Keyの順番を維持するためにsort_key=Falseを指定

    @staticmethod
    def replace_image_tag(manifest, container_image_tag: str):
        logger.info('ManifestUpdated replace_image_tag()')

        image = manifest['spec']['template']['spec']['containers'][0]['image']
        _list = image.rsplit(':')
        _list[1] = container_image_tag  # Update Tag
        image_value = ':'.join(_list)
        # update manifest
        manifest['spec']['template']['spec']['containers'][0]['image'] = image_value

        return manifest

# def replace_image_tag(manifest, container_image_tag: str):
#
#     image = manifest['spec']['template']['spec']['containers'][0]['image']
#     _list = image.rsplit(':')
#     _list[1] = container_image_tag  # Update Tag
#     image_value = ':'.join(_list)
#     manifest['spec']['template']['spec']['containers'][0]['image'] = image_value  # update manifest
#     return manifest
#
#
# def update_manifest(cd_manifest, container_image_tag: str):
#     with open(cd_manifest, 'r', encoding='utf-8') as f:
#         manifest = yaml.safe_load(f)
#         replaced_manifest = replace_image_tag(manifest, container_image_tag=container_image_tag)
#
#     with open(cd_manifest, 'w', encoding='utf-8') as f:
#         yaml.dump(
#             data=replaced_manifest,
#             stream=f,
#             sort_keys=False)  # Keyの順番を維持するためにsort_key=Falseを指定
#
#
# def get_secret(conf: dict) -> str:
#     response = secrets_manager_client.get_secret_value(
#         SecretId=conf['github_token_name'])
#     return response['SecretString']
#
# def github_manifest_update(conf: dict):
#     logger.info(f'github_manifest_update() - conf: {conf}')
#     loca_repo_path = '/tmp/repo/'  # lambda local path
#     cd_manifest = loca_repo_path + conf['github_cd_manifest']
#     github_personal_access_token = get_secret(conf=conf)  # From ASM
#
#     # git clone
#     logger.info('porcelain.clone()')
#     local_repo = porcelain.clone(
#         source=conf['github_cd_repository'],
#         branch=conf['github_branch'].encode('utf-8'),
#         password=github_personal_access_token,
#         username='not relevant',
#         target=loca_repo_path,
#         checkout=True
#     )
#
#     # update container image tag
#     update_manifest(
#         cd_manifest=cd_manifest,
#         container_image_tag=conf['container_image_tag'])
#
#     porcelain.add(repo=local_repo, paths=cd_manifest)
#
#     # git commit
#     logger.info('porcelain.commit()')
#     author = 'aws-codepipeline-lambda <lambda@example.com>'
#     porcelain.commit(
#         repo=local_repo,
#         message='Updated Image Tag.',
#         author=author,
#         committer=author
#     )
#
#     # git push
#     logger.info('porcelain.push()')
#     porcelain.push(
#         repo=local_repo,
#         remote_location=conf['github_cd_repository'],
#         refspecs=conf['github_branch'].encode('utf-8'),
#         password=github_personal_access_token,
#         username='not relevant',
#     )
#
#     shutil.rmtree(loca_repo_path)  # lambda "/tmp" cleanup


def get_secret(secret_id: str) -> str:
    response = secrets_manager_client.get_secret_value(SecretId=secret_id)
    return response['SecretString']

def extruct_user_parameters(event: dict) -> dict:
    logger.info(f'extruct_user_parameters() - event: {event}')
    job_data = event['CodePipeline.job']['data']
    user_parameters = json.loads(job_data['actionConfiguration']['configuration']['UserParameters'])
    conf = {
        'github_cd_repository': user_parameters['github_cd_repository'],
        'github_cd_manifest': user_parameters['github_cd_manifest'],  # deployment.yaml
        'github_token_name': user_parameters['github_token_name'],
        'github_branch': user_parameters['github_branch'],  # dev, stg, prd
        'container_image_tag': user_parameters['container_image_tag']['value']  # from Build Stage
    }
    return conf


def lambda_handler(event, context):
    logger.info(f'event: {event}')
    try:
        conf = extruct_user_parameters(event=event)
        lambda_local_path = '/tmp/repo/'  # lambda local path

        # github_manifest_update(conf=conf)  # Todo: ↓ refactoring

        git = Git(
            cd_repository=conf['github_cd_repository'],
            branch=conf['github_branch'],
            local_repo_path=lambda_local_path,
            target_manifest=conf['github_cd_manifest'],
            github_personal_access_token=get_secret(conf['github_token_name'])
        )

        git.clone()

        manifest = ManifestUpdated(
            target_manifest=lambda_local_path + conf['github_cd_manifest'],
            container_image_tag=conf['container_image_tag']
        )
        manifest.update_image_tag()

        git.add()
        git.commit()
        git.push()

        # Complete notification to AWS CodePipeline Stage
        logger.info('Success: Updating image tag of manifest.')
        code_pipeline_client.put_job_success_result(jobId=event['CodePipeline.job']['id'])

        # Cleanup lambda "/tmp/repo/"
        shutil.rmtree(lambda_local_path)

    except Exception as e:
        logger.info(e)
        # Failure notification to AWS CodePipeline Stage
        code_pipeline_client.put_job_failure_result(jobId=event['CodePipeline.job']['id'],
                                                    failureDetails={
                                                        'type': 'JobFailed',
                                                        'message': 'Error: GitHub Push Failed.'
                                                    })
    return
