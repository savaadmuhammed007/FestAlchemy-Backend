from django.test import TestCase
from django.contrib.auth.models import User
from programs.models import FestSettings, Category, Program
from participants.models import Team, Member, CallingList
from accounts.models import UserProfile

class CallingListPregenerationTestCase(TestCase):
    def setUp(self):
        # Create user & profile
        self.user = User.objects.create_user(username='admin', password='password')
        self.profile = UserProfile.objects.create(user=self.user, role='admin')

        # Create settings, category, program
        self.fest = FestSettings.objects.create(fest_name="Test Fest", year=2026)
        self.category = Category.objects.create(name="Sub Junior", chest_prefix=100, fest=self.fest)
        self.program = Program.objects.create(
            name="Light Music",
            category=self.category,
            fest=self.fest,
            type='single'
        )

        # Create teams & members
        self.team1 = Team.objects.create(name="Team Alpha", fest=self.fest)
        self.team2 = Team.objects.create(name="Team Beta", fest=self.fest)

        self.members = []
        for i in range(5):
            member = Member.objects.create(
                name=f"Member {i}",
                team=self.team1 if i % 2 == 0 else self.team2,
                category=self.category
            )
            member.registered_programs.add(self.program)
            self.members.append(member)

    def test_pregenerate_for_program(self):
        # Pregenerate calling lists
        CallingList.pregenerate_for_program(self.program)

        callings = list(CallingList.objects.filter(program=self.program))
        self.assertEqual(len(callings), 5)

        # Check prefixed letters
        letters = []
        for calling in callings:
            self.assertTrue(calling.calling_code.startswith("IND-"))
            letter = calling.calling_code.split('-')[1]
            letters.append(letter)
            self.assertEqual(calling.status, 'waiting')

        # Since it generates A, B, C, D, E, the set of letters should be exactly {'A', 'B', 'C', 'D', 'E'}
        self.assertEqual(set(letters), {'A', 'B', 'C', 'D', 'E'})

    def test_save_fallback(self):
        # If calling_code is not specified, it should fallback to a sequential letter
        member = self.members[0]
        calling = CallingList.objects.create(program=self.program, member=member)
        self.assertTrue(calling.calling_code.startswith("IND-"))
        letter = calling.calling_code.split('-')[1]
        self.assertEqual(letter, 'A')

        # Create another one manually, it should pick 'B'
        calling2 = CallingList.objects.create(program=self.program, member=self.members[1])
        letter2 = calling2.calling_code.split('-')[1]
        self.assertEqual(letter2, 'B')
