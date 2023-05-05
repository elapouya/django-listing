#!/usr/bin/env bash

# To be run in scripts dir
# sass minifiers have to be installed :
#
# Linux
# =====
# sudo apt install npm nodejs
# sudo npm install -g csso-cli
# sudo npm install -g google-closure-compiler
# sudo npm install -g saas
#
# MacOS
# =====
# brew install nodejs
# npm install -g csso-cli
# sudo npm i -g google-closure-compiler
# sudo gem install sass

SHOWCASE_DIR=$(dirname $(dirname $(readlink -f "$0")))
CSS_DIR=$SHOWCASE_DIR/demo/static/demo/css
JS_DIR=$SHOWCASE_DIR/demo/static/demo/js
DEMO_SCSS=$CSS_DIR/demo.scss
DEMO_CSS=$CSS_DIR/demo.css
DEMO_MIN_CSS=$CSS_DIR/demo.min.css
DEMO_JS=$JS_DIR/demo.js
DEMO_MIN_JS=$JS_DIR/demo.min.js

JS_COMPRESS="google-closure-compiler --language_out=ECMASCRIPT_2015"
CSS_COMPRESS=csso
SAAS=/usr/local/bin/sass
MINIFY=true

if [[ -d $CSS_DIR ]]
then
    set -x
    $SAAS $DEMO_SCSS ${DEMO_CSS}
    # remove css variables without any value
    mv ${DEMO_CSS} ${DEMO_CSS}.tmp
    grep -v -e '--bs.*: ;' ${DEMO_CSS}.tmp > $DEMO_CSS
    rm -f ${DEMO_CSS}.tmp
    if [[ $MINIFY == "true" ]]
    then
      $CSS_COMPRESS $DEMO_CSS --output $DEMO_MIN_CSS
    else
      cp $DEMO_CSS $DEMO_MIN_CSS
    fi
    set +x
fi

if [[ -d $JS_DIR ]]
then
    set -x
    rm -f $JS_DIR/main.min.js $DEMO_MIN_JS
    if [[ $MINIFY == "true" ]]
    then
      $JS_COMPRESS $JS_DIR/main.js > $JS_DIR/main.min.js
    else
      cp $JS_DIR/main.js $JS_DIR/main.min.js
    fi
    cat $JS_DIR/main.min.js >> $DEMO_MIN_JS
    set +x
fi
