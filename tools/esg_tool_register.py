from autogen import register_function
from tools.esg_tools import (
    show_pdf_content,
    get_pdf_page_content,
    # clustering_analysis,
    esg_analysis
)

def register_all_tools(caller_agent, executor_agent):
    """
    Registers all ESG-related tools to the given agent.
    """
    register_function(
        show_pdf_content,
        caller=caller_agent,
        executor=executor_agent,
        description="Display the full uploaded PDF text.",
        name="show_pdf_content"
    )

    register_function(
        get_pdf_page_content,
        caller=caller_agent,
        executor=executor_agent,
        description="Display the content of a specific PDF page. Takes 'page' as an integer argument.",
        name="show_pdf_page_content"
    )

    # register_function(
    #     clustering_analysis,
    #     caller=caller_agent,
    #     executor=executor_agent,
    #     description="Perform clustering analysis on the uploaded PDF content."
    # )

    register_function(
        esg_analysis,
        caller=caller_agent,
        executor=executor_agent,
        description="Extract ESG-related insights from the uploaded PDF.",
        name="esg_analysis"
    )

def register_one_agent_all_tools(agent, proxy):
    """
    Registers all ESG-related tools to the given single-agent.
    """
    tools = [
        ("show_pdf_content", "Display the full uploaded ESG report PDF text.", show_pdf_content),
        ("show_pdf_page_content", "Display the content of a specific ESG report PDF page. Takes 'page' as an integer argument.", get_pdf_page_content),
        ("esg_analysis", "Extract ESG-related insights from the uploaded ESG report PDF.", esg_analysis),
        # ("clustering_analysis", "Perform clustering analysis on the uploaded ESG report PDF content.", clustering_analysis),
    ]

    for name, description, func in tools:
        agent.register_for_llm(name=name, description=description)(func)
        proxy.register_for_execution(name=name)(func)
