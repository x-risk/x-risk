from haystack import indexes
from .models import Publication, Assessment, User

class PublicationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True, use_template=True)

    def get_model(self):
        return Publication

    def index_queryset(self, using=Publication):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.distinct().filter(
            assessment__in=Assessment.objects.filter(
                is_relevant=True
            )
        )

    def get_updated_field(self):
        return "updated"
