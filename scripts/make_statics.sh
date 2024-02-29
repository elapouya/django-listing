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

PROJECT_DIR=$(dirname $(dirname $(readlink -f "$0")))
STATIC_DIR=$PROJECT_DIR/django_listing/static/django_listing
JS_DIR=$STATIC_DIR/js
DJL_JS=$JS_DIR/django_listing.js
DJL_MIN_JS=$JS_DIR/django_listing.min.js
DUAL_LISTBOX_JS=$JS_DIR/dual-listbox.js
DUAL_LISTBOX_MIN_JS=$JS_DIR/dual-listbox.min.js

JS_COMPRESS="google-closure-compiler --language_out=ECMASCRIPT_2015"
CSS_COMPRESS=csso
SAAS=/usr/local/bin/sass
MINIFY=true

for THEME in bootstrap4 bootstrap5
do
    echo "Make $THEME theme..."
    CSS_DIR=$STATIC_DIR/$THEME/css
    DJL_SCSS=$CSS_DIR/django_listing.scss
    DJL_CSS=$CSS_DIR/django_listing.css
    DJL_MIN_CSS=$CSS_DIR/django_listing.min.css
    echo "SCSS to compile : $DJL_SCSS"
    if [[ -f $DJL_SCSS ]]
    then
        set -x
        $SAAS $DJL_SCSS ${DJL_CSS}
        # remove css variables without any value
        mv ${DJL_CSS} ${DJL_CSS}.tmp
        grep -v -e '--bs.*: ;' ${DJL_CSS}.tmp > $DJL_CSS
        rm -f ${DJL_CSS}.tmp
    fi
    if [[ $MINIFY == "true" ]]
    then
      echo "Minifying css..."
      $CSS_COMPRESS $DJL_CSS --output $DJL_MIN_CSS
    else
      echo "Copying css unminified..."
      cp $DJL_CSS $DJL_MIN_CSS
    fi
    set +x
done

if [[ -f $DJL_JS ]]
then
    set -x
    if [[ $MINIFY == "true" ]]
    then
      $JS_COMPRESS $DJL_JS > $DJL_MIN_JS
    else
      cp $DJL_JS $DJL_MIN_JS
    fi
    set +x
fi

if [[ -f $DUAL_LISTBOX_JS ]]
then
    set -x
    if [[ $MINIFY == "true" ]]
    then
      $JS_COMPRESS $DUAL_LISTBOX_JS > $DUAL_LISTBOX_MIN_JS
    else
      cp $DUAL_LISTBOX_JS $DUAL_LISTBOX_MIN_JS
    fi
    set +x
fi
