#!/usr/bin/env bash
set -e

function test_py_code() {

    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    python3 -m pip install pytest
    RABBIT_HOST="google.com" python3 -m pytest .

}

## Publish image to our docker hub repository
function publish_image() {
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
    docker-compose push transport
}

function integration_test() {
    cp env.example .env
    docker-compose build transport
    docker-compose up -d rabbit
    sleep 30
    test_py_code

    if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
        docker images
        #publish_image
    fi
}

function regression_test() {
    if [[ "$TRAVIS_BRANCH" = "testing" ]]; then
        echo "Regression Testing not supported on PR"
    else
        echo "No Yet Implmeneted"
    fi

}

if [[ "$REGRESSION" = "true" ]]; then
    regression_test
else
    integration_test
fi
