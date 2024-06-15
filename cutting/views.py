import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from . import genetic_algorithm_v2
from .forms import FileCuttingForm, ManualCuttingForm
from .models import CuttingRequest, CuttingPattern, CuttingPatternUsage


def save_cutting_request_and_generate_plot(raw_length, desired_lengths):
    # Zapisujemy żądanie cięcia
    cutting_request = CuttingRequest.objects.create(raw_length=raw_length, desired_lengths=desired_lengths)

    desired_lengths = str(desired_lengths).lstrip('[').rstrip(']').split(',')
    element_lengths = [int(el) for el in desired_lengths]
    print(element_lengths)

    ga_v2 = genetic_algorithm_v2.GeneticAlgorithm(
        beam_length=raw_length,
        element_count=len(element_lengths),
        element_lengths=element_lengths,
        population_size=70,
        generation_count=70,
        next_generation_feasible_patterns_percent=0.9,
        mutation_probability=0.9
    )

    # Obliczamy wzorce cięcia przy użyciu algorytmu
    best_solution, cutting_patterns_for_best_solution, genotype_waste, unique_element_lengths_and_count_dict = ga_v2.run()
    print(f'best_solution: {best_solution}')
    print(f'cutting_patterns_for_best_solution: {cutting_patterns_for_best_solution}')
    print(f'genotype_waste: {genotype_waste}')
    print(f'unique_element_lengths_and_count_dict: {unique_element_lengths_and_count_dict}')

    # Generowanie wykresu przy użyciu draw_cuttings_v2
    plot_uri = ga_v2.draw_cuttings(best_solution, cutting_patterns_for_best_solution, genotype_waste)

    # Tworzenie i zapisywanie wzorców cięcia
    pattern_dict = {}
    for pattern_data in cutting_patterns_for_best_solution:
        pattern_id = pattern_data['id']
        pattern = CuttingPattern.objects.create(
            id=pattern_id,  # Ustawienie id na wartość zwracaną przez algorytm
            pattern=pattern_data['pattern'],
            waste=pattern_data['waste']
        )
        pattern_dict[pattern_id] = pattern

    # Zapisywanie ilości powtórzeń każdego wzorca cięcia dla danego żądania
    for repetition, pattern_id in best_solution:
        pattern = pattern_dict.get(pattern_id)
        if pattern is not None:
            CuttingPatternUsage.objects.create(
                request=cutting_request,
                pattern=pattern,
                repetition=repetition
            )
        else:
            print(f"Pattern id {pattern_id} not found in pattern_dict")
        # Przygotowanie danych JSON dla szablonu
        beam_count = sum([el[0] for el in best_solution])
        all_elements_length = (
            sum([int(element) * int(frequency) for element, frequency in
                 unique_element_lengths_and_count_dict.items()]))
        visualization_data = {
            'genotype': best_solution,
            'chromosomes': cutting_patterns_for_best_solution,
            'genotype_waste': genotype_waste,
            'raw_length': raw_length,
            'desired_lengths': desired_lengths,
            'unique_element_lengths_and_count_dict': unique_element_lengths_and_count_dict,
            'beam_count': beam_count,
            'all_elements_length': all_elements_length,
            'surowca_utilization': (100 * all_elements_length) / (beam_count * raw_length),
        }

    json_visualization_data = mark_safe(json.dumps(visualization_data))
    print("json_visualization_data")
    [print(f'{key}: {value}\n') for key, value in visualization_data.items()]

    return cutting_request.id, plot_uri, json_visualization_data


def cutting_visualization_view(request, request_id):
    # Pobieramy żądanie cięcia z bazy danych
    request_obj = CuttingRequest.objects.get(id=request_id)
    print(int(request_obj.raw_length))

    # Uruchamiamy algorytm i generujemy wykres
    request_id, plot_uri, json_visualization_data = save_cutting_request_and_generate_plot(int(request_obj.raw_length),
                                                                                           request_obj.desired_lengths)

    # Renderujemy dane na front-end
    context = {
        'visualization_data': json_visualization_data,
        'plot_uri': plot_uri
    }

    return render(request, 'cutting_visualization.html', context)


def cutting_form_view(request):
    manual_form = ManualCuttingForm()
    file_form = FileCuttingForm()
    return render(request, 'cutting_form.html', {'manual_form': manual_form, 'file_form': file_form})


def cutting_form_manual_view(request):
    if request.method == 'POST':
        form = ManualCuttingForm(request.POST)
        if form.is_valid():
            raw_length = form.cleaned_data['raw_length']
            parts_length = form.cleaned_data['parts_length']
            parts_quantity = form.cleaned_data['parts_quantity']

            # Tworzenie rozszerzonej listy długości
            expanded_list = [length for length, quantity in zip(parts_length, parts_quantity) for _ in range(quantity)]

            print(expanded_list)  # Wyświetlanie rozszerzonej listy dla debugowania

            # Przekazanie rozszerzonej listy do funkcji obsługującej logikę cięcia
            request_id, plot_uri, json_visualization_data = save_cutting_request_and_generate_plot(raw_length, expanded_list)
            return redirect('cutting_visualization', request_id=request_id)
        else:
            print(form.errors)  # Wyświetlanie błędów formularza dla debugowania
    return redirect('cutting_form')


def cutting_form_file_view(request):
    print(request.method)
    if request.method == 'POST':
        form = FileCuttingForm(request.POST, request.FILES)
        if form.is_valid():
            parts_file = request.FILES['parts_file']
            file_data = parts_file.read().decode('utf-8').splitlines()

            raw_length = int(file_data[0])
            expanded_list = [int(el) for el in file_data[1:]]

            request_id, plot_uri, json_visualization_data = save_cutting_request_and_generate_plot(raw_length, expanded_list)
            return redirect('cutting_visualization', request_id=request_id)
        else:
            print(form.errors)  # Wyświetlanie błędów formularza dla debugowania
    return redirect('cutting_form')

def cutting_stats_view(request):
    stats = calculate_cutting_stats()
    return JsonResponse(stats)


def calculate_cutting_stats():
    cutting_requests = CuttingRequest.objects.all()
    total_requests = cutting_requests.count()

    example_stat = "Przykładowa statystyka"

    return {
        'total_requests': total_requests,
        'example_stat': example_stat,
    }
