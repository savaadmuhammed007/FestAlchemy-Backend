from django.db import models
from django.contrib.auth.models import User
from programs.models import Category, Program, FestSettings

class Team(models.Model):
    name = models.CharField(max_length=200)
    teamlead = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_teams')
    fest = models.ForeignKey(FestSettings, on_delete=models.CASCADE, null=True, blank=True, related_name='teams')

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'fest')

class Member(models.Model):
    name = models.CharField(max_length=200)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='members')
    chest_no = models.IntegerField(blank=True, null=True)
    registered_programs = models.ManyToManyField(Program, related_name='registered_members', blank=True)

    def save(self, *args, **kwargs):
        if not self.chest_no:
            prefix = self.category.chest_prefix
            # Get the global max chest_no in this category (across ALL teams in this category)
            from django.db.models import Max
            result = Member.objects.filter(category=self.category).aggregate(Max('chest_no'))
            last_max = result['chest_no__max']
            self.chest_no = (last_max + 1) if last_max is not None else (prefix + 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.chest_no})"

    class Meta:
        unique_together = ('chest_no', 'category')

class CallingList(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('absent', 'Absent'),
        ('present', 'Present'),
    ]
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='calling_lists')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='calling_lists')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='waiting')
    calling_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def pregenerate_for_program(cls, program):
        members = list(program.registered_members.all().order_by('id'))
        if not members:
            return
        
        # Get existing callings
        existing_callings = list(cls.objects.filter(program=program))
        existing_member_ids = {c.member_id for c in existing_callings}
        
        # If all registered members already have a CallingList, do nothing
        missing_members = [m for m in members if m.id not in existing_member_ids]
        if not missing_members:
            return
            
        # Get all taken lot letter codes
        taken_letters = set()
        for c in existing_callings:
            if c.calling_code:
                letter = c.calling_code.split('-')[1] if '-' in c.calling_code else c.calling_code
                taken_letters.add(letter)
                
        def get_lot_letter(index):
            result = []
            while True:
                result.append(chr(ord('A') + (index % 26)))
                index = index // 26 - 1
                if index < 0:
                    break
            return "".join(reversed(result))
            
        # Find candidates for the missing members
        candidate_letters = []
        i = 0
        while len(candidate_letters) < len(missing_members):
            letter = get_lot_letter(i)
            if letter not in taken_letters:
                candidate_letters.append(letter)
            i += 1
            
        # Shuffle candidate letters to make the assignment random
        import random
        random.shuffle(candidate_letters)
        
        # Create CallingList records for missing members
        prefix = "IND" if program.type == 'single' else "GRP"
        for member, letter in zip(missing_members, candidate_letters):
            cls.objects.get_or_create(
                program=program,
                member=member,
                defaults={
                    'calling_code': f"{prefix}-{letter}",
                    'status': 'waiting'
                }
            )

    def save(self, *args, **kwargs):
        if not self.calling_code:
            # Generate prefix based on program type
            prefix = "IND" if self.program.type == 'single' else "GRP"
            
            # Find a letter that is not already taken in this program
            existing_codes = set(
                CallingList.objects.filter(program=self.program)
                .exclude(id=self.id)
                .values_list('calling_code', flat=True)
            )
            taken_letters = set()
            for code in existing_codes:
                if code:
                    letter = code.split('-')[1] if '-' in code else code
                    taken_letters.add(letter)
                    
            def get_lot_letter(index):
                result = []
                while True:
                    result.append(chr(ord('A') + (index % 26)))
                    index = index // 26 - 1
                    if index < 0:
                        break
                return "".join(reversed(result))
                
            i = 0
            while True:
                letter = get_lot_letter(i)
                if letter not in taken_letters:
                    break
                i += 1
                
            self.calling_code = f"{prefix}-{letter}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.name} - {self.program.name} ({self.status})"
