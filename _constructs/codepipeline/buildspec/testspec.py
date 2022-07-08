testspec_object = {
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
                'pip3 install pytest pytest-cov',  # pytest-cov for coverage
                'pip3 install -r app/requirements.txt',
            ]
        },
        'build': {
            'commands': [
                'echo --- Building Docker image ---',
                'python -m pytest tests/ --junitxml=reports/pytest_results.xml --cov',  # cov: pytest-cov(coverage)
            ],
        },
    },
    'reports': {
        'pytest_reports': {  # aws_codebuild.ReportGroup(report_group_name)と同じ名前を指定する
            'files': [
                '**/*',
            ],
            'base-directory': 'reports',
            'file-format': 'JUNITXML',
        }

    }
}
