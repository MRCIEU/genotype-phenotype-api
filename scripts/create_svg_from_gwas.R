main <- function(name) {
  # vcf_file <- '/Users/wt23152/Documents/Projects/scratch/021/data/hg38.vcf.gz'

  # bcf_query <- glue::glue('/home/bcftools/bcftools query ',
  #   '--format "[%ID]\t[%CHROM]\t[%POS]\t[%LP]" ',
  #   '{vcf_file}'
  # )
  # gwas <- system(bcf_query, wait = T, intern = T)
  # gwas <- data.table::fread(text = gwas)

  # colnames(gwas) <- c('RSID', 'CHR', 'BP', 'LP')
  # gwas <- gwas |> dplyr::mutate(LP = as.numeric(LP))

  # print(head(gwas))

  gwas <- vroom::vroom(glue::glue('/Users/wt23152/Documents/Projects/scratch/021/data/{name}.tsv.gz')) |>
    dplyr::mutate(CHR = as.numeric(CHR)) |>
    dplyr::filter(!is.na(CHR)) |>
    dplyr::arrange(CHR, BP)

  chr_ranges <- gwas |>
  dplyr::group_by(CHR) |>
  dplyr::summarise(
    bp_min = min(BP),
    bp_max = max(BP),
    .groups = "drop"
  ) |>
  dplyr::mutate(
    # Calculate chromosome size
    chr_size = bp_max - bp_min,
    # Calculate cumulative position for each chromosome start
    # by summing all previous chromosome sizes plus some padding
    bp_cumulative_start = cumsum(c(0, chr_size[-dplyr::n()])) + 
                          (1:dplyr::n() - 1),
    bp_cumulative_end = bp_cumulative_start + chr_size
  )
  # Filter to significant SNPs and prepare data
  gwas <- gwas |>
    dplyr::filter(LP > -log10(0.05)) |>
    dplyr::mutate(bin = floor(BP/100000)) |>  # Create 100kb bins instead of 20kb
    dplyr::group_by(CHR, bin) |>
    dplyr::summarise(
      BP = mean(BP),
      LP = max(LP),
      .groups = "drop"
    ) |>
    dplyr::mutate(CHR = CHR) |>
    dplyr::filter(!is.na(CHR)) |>
    dplyr::mutate(color = ifelse(CHR %% 2 == 0, "dark", "light")) |>
    dplyr::arrange(CHR, BP) |>
    dplyr::left_join(chr_ranges |> dplyr::select(CHR, bp_cumulative_start, bp_min), by = "CHR") |>
    dplyr::mutate(BP_cumulative = BP - bp_min + bp_cumulative_start) |>
    # Add a flag for non-adjacent points
    dplyr::mutate(
      is_adjacent = CHR == dplyr::lead(CHR) & 
                   abs(BP - dplyr::lead(BP)) < 100000 * 2  # Allow for 2x bin size gap
    )

  # Create a second dataset with larger bins for the area
  gwas_area <- gwas |>
    dplyr::mutate(bin = floor(BP/1000000)) |>  # Create 1Mb bins for the area
    dplyr::group_by(CHR, bin) |>
    dplyr::summarise(
      BP = mean(BP),
      LP = max(LP),
      .groups = "drop"
    ) |>
    dplyr::mutate(CHR = CHR) |>
    dplyr::filter(!is.na(CHR)) |>
    dplyr::mutate(color = ifelse(CHR %% 2 == 0, "dark", "light")) |>
    dplyr::arrange(CHR, BP) |>
    dplyr::left_join(chr_ranges |> dplyr::select(CHR, bp_cumulative_start, bp_min), by = "CHR") |>
    dplyr::mutate(BP_cumulative = BP - bp_min + bp_cumulative_start)

  # Create optimized Manhattan plot with lines
  p <- ggplot2::ggplot(gwas, ggplot2::aes(x = BP_cumulative, y = LP, color = color, fill = color)) +
    # Add area with larger bins
    ggplot2::geom_area(
      data = gwas_area,
      ggplot2::aes(group = CHR),
      # alpha = 0.3,
      position = "identity"
    ) +
    # Add detailed lines
    ggplot2::geom_line(ggplot2::aes(group = CHR), linewidth = 0.5) +
    ggplot2::scale_color_manual(values = c("light" = "#444444", "dark" = "#666666")) +
    ggplot2::scale_fill_manual(values = c("light" = "#444444", "dark" = "#666666")) +
    ggplot2::scale_x_continuous(expand = c(0, 0)) +
    ggplot2::scale_y_continuous(expand = c(0, 0), limits = c(0, max(10, max(gwas$LP)))) +
    ggplot2::theme_void() +
    ggplot2::theme(
      legend.position = "none",
      plot.margin = ggplot2::margin(0, 0, 0, 0),
      plot.background = ggplot2::element_blank(),
      panel.background = ggplot2::element_blank(),
      panel.spacing = ggplot2::unit(0, "lines"),
      panel.border = ggplot2::element_blank(),
      axis.line = ggplot2::element_blank(),
      axis.ticks = ggplot2::element_blank(),
      axis.text = ggplot2::element_blank(),
      axis.title = ggplot2::element_blank()
    ) +
    ggplot2::coord_cartesian(clip = "off")

  plot_height <- 500# height in pixels
  plot_width <- 1250  # width in pixels
  # Save as SVG with reduced dimensions and DPI
  ggplot2::ggsave(
    glue::glue("manhattan_plot_{name}.svg"),
    p,
    width = plot_width/72,  # Convert to inches for ggsave
    height = plot_height/72,  # Convert to inches for ggsave
    units = "in",  # Specify inches
    limitsize = FALSE
  )
  gg_build <- ggplot2::ggplot_build(p)

  # Get the actual pixel dimensions from the plot

  # Get the coordinate ranges from the plot
  # x_range <- gg_build$layout$panel_scales_x[[1]]$range$range
  # y_range <- gg_build$layout$panel_scales_y[[1]]$range$range

  # # Scale factors to match SVG dimensions
  # width_scale <- plot_width / (x_range[2] - x_range[1])  # Scale from coordinate space to pixels
  # height_scale <- plot_height / (y_range[2] - y_range[1])  # Scale from coordinate space to pixels
  total_cumulative_bp <- max(chr_ranges$bp_cumulative_end)

  metadata <- chr_ranges |>
    dplyr::mutate(
      pixel_start = bp_to_pixel(bp_cumulative_start, total_cumulative_bp, plot_width),
      pixel_end = bp_to_pixel(bp_cumulative_end, total_cumulative_bp, plot_width)
    ) |>
    dplyr::select(CHR, bp_start = bp_cumulative_start, bp_end = bp_cumulative_end, pixel_start, pixel_end)
  metadata <- list(
    x_axis = metadata,
    y_axis = list(
      max_lp = max(gwas$LP),
      min_lp = min(gwas$LP),
      min_lp_pixel = lp_to_pixel(min(gwas$LP), min(gwas$LP), max(10, max(gwas$LP)), plot_height), 
      max_lp_pixel = lp_to_pixel(max(10, max(gwas$LP)), min(gwas$LP), max(10, max(gwas$LP)), plot_height)
    ),
    svg_width = plot_width,
    svg_height = plot_height
  )

  jsonlite::write_json(metadata, glue::glue("manhattan_plot_metadata_{name}.json"), pretty = TRUE, auto_unbox = TRUE)
}

# For x-axis (BP position to pixel)
bp_to_pixel <- function(cumulative_bp, total_cumulative_bp, svg_width = 1250) {
  # Linear rescaling: [0, total_cumulative_bp] → [0, svg_width]
  pixel <- (cumulative_bp / total_cumulative_bp) * svg_width
  return(pixel)
}

# For y-axis (LP to pixel)
lp_to_pixel <- function(lp, min_lp, max_lp, height_pixels = 500, margin_ratio = 0.0) {
  # Calculate position ratio (inverted because SVG y=0 is at top)
  position_ratio <- (lp - min_lp) / (max_lp - min_lp)

  # Account for margins (assuming 10% top/bottom)
  margin <- height_pixels * margin_ratio
  plot_height <- height_pixels - (2 * margin)

  return(height_pixels - margin - (position_ratio * plot_height))
}

main("epstein_barr")
