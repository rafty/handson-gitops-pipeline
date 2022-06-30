test_spec_object = {
    'version': '0.2',
    'env': {
        'exported-variables': ['VAR_CONTAINER_IMAGE_NAME', 'VAR_CONTAINER_IMAGE_TAG']
    },
    'phases': {
        'install': {
            'runtime-versions': {
                    'python': 3.8
            },
            'commands': [
                # 'pip3 install pytest',  # todo: add pytest-cov
                'pip3 install pytest pytest-cov',
                'pip3 install -r app/requirements.txt',
            ]
        },
        'build': {
            'commands': [
                'echo --- Building Docker image ---',
                # 'python -m pytest tests/ --junitxml=reports/pytest_results.xml',  # todo: add pytest-cov
                'python -m pytest tests/ --junitxml=reports/pytest_results.xml --cov',
            ],
        },
    },
    'reports': {
        'pytest_reports': {
            'files': [
                '**/*',
            ],
            'base-directory': 'reports',
            'file-format': 'JUNITXML',
        }

    }
}
