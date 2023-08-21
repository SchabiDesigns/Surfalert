from nbformat import read, write

def Remove_Output(Book):

    for cell in Book.cells:

        if hasattr(cell, "outputs"):

            cell.outputs = []

        if hasattr(cell, "prompt_number"):

            del cell["prompt_number"]


if __name__ == "__main__":
    Book= read(open("Meteomatics_EDA.ipynb"), 4)
    Remove_Output(Book)
    write(Book, open("Meteomatics_EDA_restore.ipynb", "w"), 4)
    
    