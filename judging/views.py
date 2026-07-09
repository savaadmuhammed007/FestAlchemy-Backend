from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import role_required
from .models import Marksheet
from .forms import MarksheetForm
from django.contrib import messages
from participants.models import CallingList
from programs.models import Program

@role_required('judge')
def judge_dashboard(request):
    # Get all programs that have marksheets for this judge
    all_programs = Program.objects.filter(marksheets__judge=request.user).distinct()
    
    pending_programs = []
    finalized_programs = []
    
    for program in all_programs:
        # Check if there are any unsubmitted marksheets for this judge in this program
        has_pending = Marksheet.objects.filter(
            program=program, 
            judge=request.user, 
            submitted=False
        ).exists()
        
        # Calculate completion stats
        total_sheets = Marksheet.objects.filter(program=program, judge=request.user).count()
        submitted_sheets = Marksheet.objects.filter(program=program, judge=request.user, submitted=True).count()
        
        program.total_sheets = total_sheets
        program.submitted_sheets = submitted_sheets
        
        if has_pending:
            pending_programs.append(program)
        else:
            finalized_programs.append(program)
            
    return render(request, 'judging/judge_dashboard.html', {
        'pending_programs': pending_programs,
        'finalized_programs': finalized_programs,
    })

@role_required('judge')
def evaluate_list(request, program_id):
    program = get_object_or_404(Program, id=program_id)
    marksheets = Marksheet.objects.filter(program=program, judge=request.user).select_related('member')
    
    # Enrichment for judge codes
    for sheet in marksheets:
        calling = CallingList.objects.filter(program=sheet.program, member=sheet.member).first()
        if calling and '-' in calling.calling_code:
            sheet.judge_code = calling.calling_code.split('-')[1]
        else:
            sheet.judge_code = calling.calling_code if calling else "N/A"
            
    pending_marksheets = []
    submitted_marksheets = []
    for sheet in marksheets:
        if sheet.submitted:
            submitted_marksheets.append(sheet)
        else:
            pending_marksheets.append(sheet)
            
    return render(request, 'judging/evaluate_list.html', {
        'program': program,
        'pending_marksheets': pending_marksheets,
        'submitted_marksheets': submitted_marksheets,
    })

@role_required('judge')
def evaluate(request, spreadsheet_id):
    marksheet = get_object_or_404(Marksheet, id=spreadsheet_id, judge=request.user)
    calling = CallingList.objects.filter(program=marksheet.program, member=marksheet.member).first()
    
    if calling and '-' in calling.calling_code:
        marksheet.judge_code = calling.calling_code.split('-')[1]
    else:
        marksheet.judge_code = calling.calling_code if calling else "N/A"
    
    if marksheet.submitted:
        messages.info(request, "This marksheet has already been submitted.")
        return redirect('evaluate_list', program_id=marksheet.program.id)
        
    if request.method == 'POST':
        form = MarksheetForm(request.POST, instance=marksheet)
        if form.is_valid():
            sheet = form.save(commit=False)
            if 'submit' in request.POST:
                sheet.submitted = True
                messages.success(request, "Evaluations submitted successfully!")
            else:
                messages.success(request, "Draft saved successfully.")
            sheet.save()
            return redirect('evaluate_list', program_id=marksheet.program.id)
    else:
        form = MarksheetForm(instance=marksheet)
        
    return render(request, 'judging/evaluate.html', {
        'form': form,
        'marksheet': marksheet
    })
