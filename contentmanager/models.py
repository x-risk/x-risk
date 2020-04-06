import datetime
from django import forms
from django.db import models
from django.db.models import Q
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.tags import ClusterTaggableManager
from taggit.models import TaggedItemBase, Tag as TaggitTag
from wagtail.admin.edit_handlers import FieldPanel, FieldRowPanel, MultiFieldPanel, \
    InlinePanel, PageChooserPanel, StreamFieldPanel
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core.fields import RichTextField
from wagtail.core.fields import StreamField
from wagtail.core.models import Page, Orderable
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.documents.edit_handlers import DocumentChooserPanel
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.snippets.models import register_snippet
from .utils import MarkdownField, MarkdownPanel
from wagtail.core import blocks
from wagtail.core.blocks import TextBlock, StructBlock, StreamBlock, FieldBlock, CharBlock, RichTextBlock, RawHTMLBlock, ChoiceBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.search import index
from contentmanager.wagtail_hooks import register_extra_feature

class DefaultPageTag(TaggedItemBase):
    content_object = ParentalKey('contentmanager.DefaultPage', related_name='tagged_items')

class DefaultPage(RoutablePageMixin, Page):
    body = StreamField([
        ('heading', blocks.CharBlock(classname="full title")),
        ('paragraph', blocks.RichTextBlock("")),
        ('image', ImageChooserBlock()),
        ('table', TableBlock(template='core/tableblock.html')),
    ])
    tags = ClusterTaggableManager(through=DefaultPageTag, blank=True)
    date = models.DateField("Post date", default=datetime.datetime.today)
    feed_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    api_fields = ['body', 'tags', 'date', 'feed_image']

    content_panels = Page.content_panels + [
        FieldPanel('date'),
        StreamFieldPanel('body'),
    ]

    promote_panels = Page.promote_panels + [
        ImageChooserPanel('feed_image'),
        FieldPanel('tags'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('body'),
    ]

    class Meta:
        verbose_name = "Standard page"


# Global Streamfield definition

class PullQuoteBlock(StructBlock):
    quote = TextBlock("quote title")
    attribution = CharBlock()

    class Meta:
        icon = "openquote"

class ImageFormatChoiceBlock(FieldBlock):
    field = forms.ChoiceField(choices=(
        ('left', 'Wrap left'), ('right', 'Wrap right'), ('mid', 'Mid width'), ('full', 'Full width'),
    ))

class HTMLAlignmentChoiceBlock(FieldBlock):
    field = forms.ChoiceField(choices=(
        ('normal', 'Normal'), ('full', 'Full width'),
    ))

class ImageBlock(StructBlock):
    image = ImageChooserBlock()
    caption = RichTextBlock()
    alignment = ImageFormatChoiceBlock()

class AlignedHTMLBlock(StructBlock):
    html = RawHTMLBlock()
    alignment = HTMLAlignmentChoiceBlock()

    class Meta:
        icon = "code"

class IconBlock(StructBlock):
    position = ChoiceBlock(choices=(
        ('left', 'Left'), ('center', 'Center'), ('right', 'Right')), default='center'
    )
    icon = TextBlock("")
    icon_colour = TextBlock("")
    content = RichTextBlock("")

class TaggedArticlesBlock(StructBlock):
    tag = TextBlock("")

class MainStreamBlock(StreamBlock):
    row = IconBlock(icon="pilcrow")
    third_column = IconBlock(icon="pilcrow")
    half_column = IconBlock(icon="pilcrow")
    pullquote = PullQuoteBlock()
    tagged_articles = TaggedArticlesBlock()
    aligned_html = AlignedHTMLBlock(icon="code", label='Raw HTML')

# A couple of abstract classes that contain commonly used fields

class LinkFields(models.Model):
    link_external = models.URLField("External link", blank=True)
    link_page = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        related_name='+'
    )
    link_document = models.ForeignKey(
        'wagtaildocs.Document',
        null=True,
        blank=True,
        related_name='+'
    )

    @property
    def link(self):
        if self.link_page:
            return self.link_page.url
        elif self.link_document:
            return self.link_document.url
        else:
            return self.link_external

    panels = [
        FieldPanel('link_external'),
        PageChooserPanel('link_page'),
        DocumentChooserPanel('link_document'),
    ]

    api_fields = ['link_external', 'link_page', 'link_document']

    class Meta:
        abstract = True

# Carousel items

class CarouselItem(LinkFields):
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    embed_url = models.URLField("Embed URL", blank=True)
    caption = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    panels = [
        ImageChooserPanel('image'),
        FieldPanel('embed_url'),
        FieldPanel('caption'),
        FieldPanel('description'),
        MultiFieldPanel(LinkFields.panels, "Link"),
    ]

    api_fields = ['image', 'embed_url', 'caption', 'description'] + LinkFields.api_fields

    class Meta:
        abstract = True

# Home Page

class HomePageCarouselItem(Orderable, CarouselItem):
    page = ParentalKey('contentmanager.HomePage', related_name='carousel_items')

class HomePage(RoutablePageMixin, Page):
    body = StreamField(MainStreamBlock())

    content_panels = Page.content_panels + [
        InlinePanel('carousel_items', label="Carousel items"),
        StreamFieldPanel('body'),
    ]

    promote_panels = Page.promote_panels

    search_fields = Page.search_fields + [
        index.SearchField('body'),
    ]

    api_fields = ['carousel_items', 'body']

    def get_context(self, request, *args, **kwargs):
        context = super(HomePage, self).get_context(request, *args,**kwargs)
        context['search_type'] = getattr(self, 'search_type', "")
        context['search_term'] = getattr(self, 'search_term', "")
        return context

    class Meta:
        verbose_name = "Home page"
        

@register_snippet
class Tag(TaggitTag):
    class Meta:
        proxy = True
