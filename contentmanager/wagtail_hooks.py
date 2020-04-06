from django.utils.html import format_html_join
from django.conf import settings

import wagtail.admin.rich_text.editors.draftail.features as draftail_features
from wagtail.admin.rich_text.converters.html_to_contentstate import InlineStyleElementHandler
from wagtail.core import hooks

from .rich_text import AnchorEntityElementHandler, anchor_entity_decorator, AnchorIndentifierEntityElementHandler, anchor_identifier_entity_decorator

@hooks.register('register_rich_text_features')
def register_extra_feature(features):

    feature_name = 'superscript'
    type_ = 'SUPERSCRIPT'
    tag = 'sup'

    control = {
        'type': type_,
        'label': '^',
        'description': 'Superscript',
    }

    features.register_editor_plugin(
        'draftail', feature_name, draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        'from_database_format': {tag: InlineStyleElementHandler(type_)},
        'to_database_format': {'style_map': {type_: tag}},
    }

    features.default_features.append(feature_name)
    features.register_converter_rule('contentstate', feature_name, db_conversion)

    feature_name = 'subscript'
    type_ = 'SUBSCRIPT'
    tag = 'sub'

    control = {
        'type': type_,
        'label': 'v',
        'description': 'Subscript',
    }

    features.register_editor_plugin(
        'draftail', feature_name, draftail_features.InlineStyleFeature(control)
    )

    db_conversion = {
        'from_database_format': {tag: InlineStyleElementHandler(type_)},
        'to_database_format': {'style_map': {type_: tag}},
    }

    features.default_features.append(feature_name)
    features.register_converter_rule('contentstate', feature_name, db_conversion)

#    feature_name = 'code'
#    type_ = 'MONOSPACE'
#    tag = 'code'

#    control = {
#        'type': type_,
#        'label': 'CODE',
#        'description': 'Code',
#    }

#    features.register_editor_plugin(
#        'draftail', feature_name, draftail_features.InlineStyleFeature(control)
#    )

#    db_conversion = {
#        'from_database_format': {tag: InlineStyleElementHandler(type_)},
#        'to_database_format': {'style_map': {type_: tag}},
#    }

#    features.default_features.append(feature_name)
#    features.register_converter_rule('contentstate', feature_name, db_conversion)


    features.default_features.append('anchor')
    """
    Registering the `anchor` feature, which uses the `ANCHOR` Draft.js entity type,
    and is stored as HTML with a `<a data-anchor href="#my-anchor">` tag.
    """
    feature_name = 'anchor'
    type_ = 'ANCHOR'

    control = {
        'type': type_,
        'label': '#',
        'description': 'Anchor',
    }

    features.register_editor_plugin(
        'draftail', feature_name, draftail_features.EntityFeature(control)
    )

    features.register_converter_rule('contentstate', feature_name, {
        # Note here that the conversion is more complicated than for blocks and inline styles.
        'from_database_format': {'a[data-anchor]': AnchorEntityElementHandler(type_)},
        'to_database_format': {'entity_decorators': {type_: anchor_entity_decorator}},
    })

    features.default_features.append('anchor-identifier')
    """
    Registering the `anchor-identifier` feature, which uses the `ANCHOR-IDENTIFIER` Draft.js entity type,
    and is stored as HTML with a `<a data-anchor href="#my-anchor" id="my-anchor">` tag.
    """
    feature_name = 'anchor-identifier'
    type_ = 'ANCHOR-IDENTIFIER'

    control = {
        'type': type_,
        'label': '<#id>',
        'description': 'Anchor Identifier',
    }

    features.register_editor_plugin(
        'draftail', feature_name, draftail_features.EntityFeature(control)
    )

    features.register_converter_rule('contentstate', feature_name, {
        # Note here that the conversion is more complicated than for blocks and inline styles.
        # 'from_database_format': {'a[data-anchor][id]': AnchorIndentifierEntityElementHandler(type_)},
        'from_database_format': {'a[data-id]': AnchorIndentifierEntityElementHandler(type_)},
        'to_database_format': {'entity_decorators': {type_: anchor_identifier_entity_decorator}},
    })


@hooks.register('insert_editor_js')
def insert_editor_js_anchor():
    js_files = [
        # We require this file here to make sure it is loaded before the other.
        'wagtailadmin/js/draftail.js',
        'wagtail_draftail_anchor.js',
    ]
    js_includes = format_html_join('\n', '<script src="{0}{1}"></script>',
        ((settings.STATIC_URL, filename) for filename in js_files)
    )
    return js_includes
