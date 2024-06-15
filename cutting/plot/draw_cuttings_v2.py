import matplotlib
matplotlib.use('Agg')  # Wyłączenie trybu interaktywnego

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import io
import base64


def draw_cuttings_v2(genotype, chromosomes, unique_elements_length_dict, genotype_waste):

    print(f'unique_elements_length_dict: {unique_elements_length_dict}')
    unique_elements_length = [int(el) for el in unique_elements_length_dict.keys()]
    print(f'unique_elements_length: {unique_elements_length}')
    all_elements_length = (
        sum([int(element) * int(frequency) for element, frequency in unique_elements_length_dict.items()]))
    beam_count = sum([el[0] for el in genotype])
    beam_length = chromosomes[0]['stock_size']

    # Rysowanie wykresu
    fig, ax = plt.subplots()

    # Iteracja po każdym zestawie danych
    for i, data in enumerate(chromosomes):
        # Suma długości cięć
        total_cut_length = sum([length * count for length, count in zip(unique_elements_length, data['pattern'])])

        # Dodawanie prostokątów reprezentujących cięcia
        left = 0
        for j, (cut_length, cut_count) in enumerate(zip(unique_elements_length, data['pattern'])):
            for _ in range(cut_count):  # Uwzględnianie ilości wystąpień elementu
                color = cm.viridis(j / len(unique_elements_length))  # Wybieranie koloru z palety
                ax.barh(y=i, width=cut_length, left=left, color=color, edgecolor='black', linewidth=0.5)

                # Dodawanie etykiety z długością elementu
                ax.text(left + cut_length / 2, i + 0.2, str(cut_length), ha='center', va='center', color='black',
                        fontsize=8)

                left += cut_length

        # Dodanie prostokąta reprezentującego ilość odpadu, jeśli jest większa od zera
        if data['waste'] > 0:
            ax.barh(y=i, width=data['waste'], left=left, color='white', edgecolor='black', linewidth=0.5)

            # Dodanie etykiety z ilością odpadu
            ax.text(left + data['waste'] / 2, i + 0.2, str(data['waste']), ha='center', va='center', color='black',
                    fontsize=8)

    # Ustawienie wysokości
    ax.set_ylim([-0.5, len(chromosomes) - 0.5])
    ax.set_yticks(range(len(chromosomes)))
    ax.set_yticklabels([f'{frequency_id[0]} x ' for frequency_id in genotype])

    ax.set_xlim([0, beam_length])

    # Dodanie dodatkowego tekstu poniżej osi X
    ax.text(0.5, -0.095,
            f'Zużyto {beam_count} belek o długości {beam_length}\n'
            f'Łączna długość elementów: {all_elements_length}\n'
            f'Elementów surowca wykorzystano: {beam_count * beam_length} ({(100 * all_elements_length) / (beam_count * beam_length):.2f}%)',
            ha='center', va='center', transform=ax.transAxes)
    # Dodanie dodatkowego tekstu powyżej grafiki
    ax.text(0.5, 1.05, f'Łączna długość odpadów: {genotype_waste}\n', ha='center', va='center', transform=ax.transAxes)

    # Dodanie dodatkowego tekstu powyżej grafiki
    ax.text(0.5, 1.05, f'Łączna długość odpadów: {genotype_waste}\n', ha='center', va='center', transform=ax.transAxes)

    # Zwiększenie rozmiaru okna wykresu
    fig.set_size_inches(10, 7)  # Możesz dostosować szerokość i wysokość według własnych potrzeb

    # Convert plot to PNG image
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = 'data:image/png;base64,' + string.decode('utf-8')
    buf.close()
    plt.close(fig)

    print(f'\nŁączna długość odpadów: {genotype_waste}\n'
          f'Zużyto: {beam_count} belek o długości {beam_length}\n'
          f'Łączna długość elementów: {all_elements_length}\n'
          f'Elementów surowca wykorzystano: {beam_count * beam_length} ({(100 * all_elements_length) / (beam_count * beam_length):.2f}%)')

    return uri
