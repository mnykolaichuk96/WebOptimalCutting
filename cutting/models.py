from django.db import models


class CuttingRequest(models.Model):
    raw_length = models.FloatField()
    desired_lengths = models.TextField()  # Lista żądanych długości jako tekst
    created_at = models.DateTimeField(auto_now_add=True)


class CuttingPattern(models.Model):
    id = models.CharField(max_length=32, primary_key=True)  # Ustawienie id jako CharField
    pattern = models.TextField()  # Wzorzec cięcia jako tekst
    waste = models.FloatField()  # Ilość odpadów


class CuttingPatternUsage(models.Model):
    request = models.ForeignKey(CuttingRequest, related_name='pattern_usages', on_delete=models.CASCADE)
    pattern = models.ForeignKey(CuttingPattern, related_name='usages', on_delete=models.CASCADE)
    repetition = models.IntegerField()  # Liczba powtórzeń tego wzorca cięcia
