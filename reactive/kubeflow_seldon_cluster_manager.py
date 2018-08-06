import os

from charmhelpers.core import hookenv
from charms.reactive import set_flag, endpoint_from_flag
from charms.reactive import when, when_not

from charms import layer


@when_not('endpoint.redis.available')
def blocked():
    goal_state = hookenv.goal_state()
    if 'redis' in goal_state['relations']:
        layer.status.waiting('waiting for redis')
    else:
        layer.status.blocked('missing relation to redis')


@when('layer.docker-resource.cluster-manager-image.available')
@when('endpoint.redis.available')
@when_not('charm.kubeflow-seldon-cluster-manager.started')
def start_charm():
    layer.status.maintenance('configuring container')

    config = hookenv.config()
    image_info = layer.docker_resource.get_info('cluster-manager-image')
    redis = endpoint_from_flag('endpoint.redis.available')
    redis_application_name = redis.all_joined_units[0].application_name
    redis_service_name = 'juju-{}'.format(redis_application_name)
    model = os.environ['JUJU_MODEL_NAME']
    java_opts = config['java-opts']
    spring_opts = config['spring-opts']
    engine_image = config['engine-image']

    layer.caas_base.pod_spec_set({
        'containers': [
            {
                'name': 'seldon-cluster-manager',
                'imageDetails': {
                    'imagePath': image_info.registry_path,
                    'username': image_info.username,
                    'password': image_info.password,
                },
                'ports': [
                    {
                        'name': 'cluster-manager',
                        'containerPort': 8080,
                    },
                ],
                'config': {
                    'SELDON_CLUSTER_MANAGER_REDIS_HOST': redis_service_name,
                    'SELDON_CLUSTER_MANAGER_POD_NAMESPACE': model,
                    'JAVA_OPTS': java_opts,
                    'SPRING_OPTS': spring_opts,
                    'ENGINE_CONTAINER_IMAGE_AND_VERSION': engine_image,
                },
                'files': [
                ],
            },
        ],
    })

    layer.status.maintenance('creating container')
    set_flag('charm.kubeflow-seldon-cluster-manager.started')
