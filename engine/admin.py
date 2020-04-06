from django.contrib import admin
from .models import Topic, Source, SearchString, Search, Publication, Assessment, Profile, AssessmentStatus, HumanPrediction, MLModel, MLPrediction, Log

admin.site.register(Topic)
admin.site.register(Source)
admin.site.register(SearchString)
admin.site.register(Search)
admin.site.register(Publication)
admin.site.register(Assessment)
admin.site.register(Profile)
admin.site.register(AssessmentStatus)
admin.site.register(HumanPrediction)
admin.site.register(MLModel)
admin.site.register(MLPrediction)
admin.site.register(Log)
